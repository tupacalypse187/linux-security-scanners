# 🛡️ ClamAV Scan-to-SIEM: Complete Guide

> AlmaLinux 9 · Amazon Linux 2 · Amazon Linux 2023 · JSON Output · Systemd Timer · SIEM Ingestion

---

## 📋 Table of Contents

- [🔍 What Was Discovered](#-what-was-discovered)
- [📊 ClamScan Output Comparison](#-clamscan-output-comparison)
- [🐧 OS-Specific Findings](#-os-specific-findings)
- [⚙️ JSON Conversion](#-json-conversion)
- [🐙 Docker Base Images](#-docker-base-images)
- [🤖 Systemd Service + Timer](#-systemd-service--timer)
- [📥 SIEM Ingestion Strategy](#-siem-ingestion-strategy)
- [🔍 Manual Checks with jq](#-manual-checks-with-jq)
- [📁 File Inventory](#-file-inventory)
- [🚀 Step-by-Step Reproduction](#-step-by-step-reproduction)
- [🧹 Cleanup](#-cleanup)

---

## 🔍 What Was Discovered

| Finding | Detail |
|---------|--------|
| **ClamAV Version** | 1.5.2 (AL9, AL2023 via Cisco Talos RPM) · 1.4.3 (AL2 via EPEL) |
| **`--json` flag** | ❌ **Not available** in any tested build (EPEL or Cisco RPM). Custom Python parsing required. |
| **`--no-summary` flag** | ✅ Works on all three. Suppresses the `----------- SCAN SUMMARY -----------` block entirely. |
| **Definitions** | ~3.6M signatures after `freshclam` (daily: 27979, main: 63, bytecode: 339) |
| **Docker Desktop** | ✅ All testing done on Windows 11 Docker Desktop with volume mounts |
| **Amazon Linux 2023** | Requires Cisco Talos RPM (no EPEL ClamAV available). Needs `shadow-utils` for `useradd`, `--allowerasing` to resolve `libcurl` conflict, and manual `freshclam.conf` creation at `/usr/local/etc/`. |

---

## 📊 ClamScan Output Comparison

### ✅ Default Output (with summary)

```
/etc/hostname: OK
/etc/hosts: OK
/etc/passwd: OK
/etc/resolv.conf: OK

----------- SCAN SUMMARY -----------
Known viruses: 3627837
Engine version: 1.5.2
Scanned directories: 0
Scanned files: 4
Infected files: 0
Data scanned: 0.00 MB
Data read: 0.00 MB (ratio 0.00:1)
Time: 7.349 sec (0 m 7 s)
Start Date: 2026:04:22 10:11:37
End Date:   2026:04:22 10:11:45
```

### 🚫 With `--no-summary` Flag

```
/etc/hostname: OK
/etc/hosts: OK
/etc/passwd: OK
/etc/resolv.conf: OK
```

### 📝 Key Difference

The `--no-summary` flag suppresses the **entire** `----------- SCAN SUMMARY -----------` block. For SIEM ingestion:
- **Without `--no-summary`** → JSON includes `scan_summary` object with engine version, virus count, infected files, timing
- **With `--no-summary`** → JSON only contains per-file results (lighter payload, faster parsing)

> 💡 **Recommendation:** Keep the summary **ON** for SIEM. The metadata (infected_files count, scan duration, definition version) is valuable for alerting and dashboards.

---

## 🐧 OS-Specific Findings

### Comparison Matrix

| Feature | 🎩 AlmaLinux 9 | 📦 Amazon Linux 2 | ☁️ Amazon Linux 2023 |
|---------|----------------|-------------------|---------------------|
| **ClamAV Version** | 1.5.2 | 1.4.3 | 1.5.2 |
| **Install Method** | Cisco Talos RPM | EPEL (`amazon-linux-extras`) | Cisco Talos RPM |
| **Config Location** | `/usr/local/etc/freshclam.conf` | `/etc/freshclam.conf` | `/usr/local/etc/freshclam.conf` |
| **Binary Location** | `/usr/local/bin/clamscan` | `/usr/bin/clamscan` | `/usr/local/bin/clamscan` |
| **`--json` Support** | ❌ No | ❌ No | ❌ No |
| **`--no-summary`** | ✅ Yes | ✅ Yes | ✅ Yes |
| **Build Gotchas** | `shadow-utils` needed; `--allowerasing` for `libcurl` conflict | None (EPEL package works) | `shadow-utils` needed; `--allowerasing` for `libcurl` conflict |

### Why the Cisco Talos RPM for AL9 and AL2023?

AlmaLinux 9 and Amazon Linux 2023 use the Cisco Talos RPM for ClamAV 1.5.2:

```
https://github.com/Cisco-Talos/clamav/releases/download/clamav-1.5.2/clamav-1.5.2.linux.x86_64.rpm
```

Previously, AlmaLinux 9 used EPEL packages (ClamAV 1.4.3). Moving to the Cisco RPM provides the latest version with CVE fixes.

**Amazon Linux 2 stays on EPEL** (ClamAV 1.4.3) because the Cisco Talos RPM requires glibc 2.28, but AL2 ships glibc 2.26. Symlinks at `/usr/local/bin/clamscan` and `/usr/local/bin/freshclam` ensure the shared systemd service file works across all OSes.

**Gotchas resolved during testing:**

1. **`libcurl` conflict** — AlmaLinux 9 and Amazon Linux 2023 ship `libcurl-minimal` which conflicts with the `libcurl` the RPM needs. Fix: `dnf install --allowerasing`.
2. **No `useradd`** — Minimal images lack `shadow-utils`. Fix: install `shadow-utils`.
3. **Missing `freshclam.conf`** — The Cisco RPM installs to `/usr/local/` prefix but doesn't create a config file. Fix: write `freshclam.conf` to `/usr/local/etc/` with `DatabaseMirror` and `DatabaseDirectory` directives.
4. **No `clamav` user** — The RPM post-install script doesn't create the `clamav` system user. Fix: `useradd -r -s /sbin/nologin clamav`.

---

## ⚙️ JSON Conversion

Since none of the tested ClamAV builds support `--json`, we parse the text output with Python.

### Architecture

```
clamscan -r /path/to/scan
         │
         ▼  (pipe stdout)
clamscan-to-json.py
         │
         ├──▶ stdout (captured by systemd journal)
         │
         └──▶ /var/log/clamav/clamscan.jsonl (append, one line per scan)
```

### JSON Schema

**With summary:**
```json
{
  "file_results": [
    {"file": "/etc/hostname", "status": "OK"},
    {"file": "/etc/hosts", "status": "OK"}
  ],
  "scan_summary": {
    "known_viruses": 3627837,
    "engine_version": "1.5.2",
    "scanned_directories": 0,
    "scanned_files": 4,
    "infected_files": 0,
    "data_scanned": "0.00 MB",
    "data_read": "0.00 MB (ratio 0.00:1)",
    "time": "7.349 sec (0 m 7 s)",
    "start_date": "2026:04:22 10:11:37",
    "end_date": "2026:04:22 10:11:45"
  },
  "hostname": "server01.example.com",
  "timestamp": "2026-04-22T10:11:45Z"
}
```

**Without summary (`--no-summary`):**
```json
{
  "file_results": [
    {"file": "/etc/hostname", "status": "OK"}
  ],
  "hostname": "server01.example.com",
  "timestamp": "2026-04-22T10:11:45Z"
}
```

### SIEM-Ready Single Line

Each scan produces **one line** of JSON. The JSONL file grows with one line per scan:

```
{"file_results":[{"file":"/etc/hostname","status":"OK"}],"scan_summary":{"known_viruses":3627837,...},"hostname":"server01","timestamp":"2026-04-22T10:11:45Z"}
{"file_results":[{"file":"/etc/hostname","status":"OK"}],"scan_summary":{"known_viruses":3627837,...},"hostname":"server01","timestamp":"2026-04-23T09:15:22Z"}
{"file_results":[{"file":"/tmp/eicar.com","status":"FOUND Eicar-Test-Signature"}],"scan_summary":{"known_viruses":3627837,...,"infected_files":1},"hostname":"server01","timestamp":"2026-04-24T11:03:44Z"}
```

---

## 🐙 Docker Base Images

Pre-built images with ClamAV + fresh definitions baked in for fast testing.

Build context is the project root (`linux-security-scanners/`), so all COPY paths are relative to that root.

### 🎩 AlmaLinux 9

```dockerfile
# clamav/almalinux9/Dockerfile
FROM almalinux:9

COPY clamav/shared/clamscan-to-json.py /usr/local/bin/clamscan-to-json.py

RUN dnf install -y python3 wget shadow-utils \
    && wget -q https://github.com/Cisco-Talos/clamav/releases/download/clamav-1.5.2/clamav-1.5.2.linux.x86_64.rpm -O /tmp/clamav.rpm \
    && echo "9c7e0532e718b3aec294ec08be7fdbd39969d922bb7bb93cc06d1da890c39848  /tmp/clamav.rpm" | sha256sum -c - \
    && dnf install -y --allowerasing /tmp/clamav.rpm \
    && rm -f /tmp/clamav.rpm \
    && chmod +x /usr/local/bin/clamscan-to-json.py \
    && useradd -r -s /sbin/nologin clamav || true \
    && mkdir -p /var/lib/clamav \
    && chown clamav:clamav /var/lib/clamav \
    && echo "DatabaseMirror database.clamav.net" > /usr/local/etc/freshclam.conf \
    && echo "DatabaseDirectory /var/lib/clamav" >> /usr/local/etc/freshclam.conf \
    && freshclam \
    && dnf clean all
```

```bash
docker build -t almalinux9-clamav:latest -f clamav/almalinux9/Dockerfile .
```

### 📦 Amazon Linux 2

```dockerfile
# clamav/amazonlinux2/Dockerfile
FROM amazonlinux:2

COPY clamav/shared/clamscan-to-json.py /usr/local/bin/clamscan-to-json.py

RUN amazon-linux-extras install -y epel \
    && yum install -y clamav clamav-update python3 \
    && chmod +x /usr/local/bin/clamscan-to-json.py \
    && ln -s /usr/bin/freshclam /usr/local/bin/freshclam \
    && ln -s /usr/bin/clamscan /usr/local/bin/clamscan \
    && freshclam \
    && yum clean all
```

```bash
docker build -t amazonlinux2-clamav:latest -f clamav/amazonlinux2/Dockerfile .
```

### ☁️ Amazon Linux 2023

```dockerfile
# clamav/amazonlinux2023/Dockerfile
FROM amazonlinux:2023

COPY clamav/shared/clamscan-to-json.py /usr/local/bin/clamscan-to-json.py

RUN dnf install -y python3 wget shadow-utils \
    && wget -q https://github.com/Cisco-Talos/clamav/releases/download/clamav-1.5.2/clamav-1.5.2.linux.x86_64.rpm -O /tmp/clamav.rpm \
    && echo "9c7e0532e718b3aec294ec08be7fdbd39969d922bb7bb93cc06d1da890c39848  /tmp/clamav.rpm" | sha256sum -c - \
    && dnf install -y --allowerasing /tmp/clamav.rpm \
    && rm -f /tmp/clamav.rpm \
    && chmod +x /usr/local/bin/clamscan-to-json.py \
    && useradd -r -s /sbin/nologin clamav || true \
    && mkdir -p /var/lib/clamav \
    && chown clamav:clamav /var/lib/clamav \
    && echo "DatabaseMirror database.clamav.net" > /usr/local/etc/freshclam.conf \
    && echo "DatabaseDirectory /var/lib/clamav" >> /usr/local/etc/freshclam.conf \
    && freshclam \
    && dnf clean all
```

```bash
docker build -t amazonlinux2023-clamav:latest -f clamav/amazonlinux2023/Dockerfile .
```

> ⚠️ Definitions are frozen at build time. For production, run `freshclam` before each scan (the systemd service handles this).

---

## 🤖 Systemd Service + Timer

### Service: `clamav-scan.service`

Runs the scan, pipes output to the JSON converter.

```ini
[Unit]
Description=ClamAV On-Demand Scan
Documentation=man:clamscan(1)
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=root

# Update definitions before scanning
ExecStartPre=/usr/local/bin/freshclam --quiet

# Run clamscan with summary, pipe output to JSON converter
# Change SCAN_PATH to your target directory (e.g., /home, /var/www, /)
ExecStart=/bin/bash -c '/usr/local/bin/clamscan -r / | /usr/local/bin/clamscan-to-json.py'

# Timeout — large scans may take a while (default: 24h)
TimeoutStartSec=86400

# Resource limits
IOSchedulingClass=idle
CPUSchedulingPolicy=idle

[Install]
WantedBy=multi-user.target
```

> **AL9, AL2023:** The Cisco Talos RPM installs binaries to `/usr/local/bin/`. **AL2:** EPEL installs to `/usr/bin/`; symlinks at `/usr/local/bin/` ensure the shared service file works across all OSes.

### Timer: `clamav-scan.timer`

Fires the service **daily at a random time** (spread over 24h to avoid thundering herd).

```ini
[Unit]
Description=Daily ClamAV Scan Timer

[Timer]
# Run daily
OnCalendar=*-*-* 00:00:00

# Spread start randomly within a 24h window so hosts don't all hit at once
RandomizedDelaySec=86400

# If the machine was off at scheduled time, run on next boot
Persistent=true

# Don't run if we already ran today (prevents duplicate on boot)
AccuracySec=1h

[Install]
WantedBy=timers.target
```

| Timer Field | Value | Purpose |
|-------------|-------|---------|
| `OnCalendar` | `*-*-* 00:00:00` | Earliest possible start: midnight daily |
| `RandomizedDelaySec` | `86400` | Random delay up to 24h — each host runs at a different time |
| `Persistent` | `true` | If the machine was off, run on next boot |
| `AccuracySec` | `1h` | Limit drift to 1h for catch-up runs |

### Install on Host

```bash
# 1. Copy files into place
sudo cp clamav/shared/clamscan-to-json.py /usr/local/bin/
sudo chmod +x /usr/local/bin/clamscan-to-json.py

sudo cp clamav/shared/clamav-scan.service /etc/systemd/system/
sudo cp clamav/shared/clamav-scan.timer /etc/systemd/system/

# 2. Create log directory
sudo mkdir -p /var/log/clamav
sudo touch /var/log/clamav/clamscan.jsonl
sudo chmod 640 /var/log/clamav/clamscan.jsonl

# 3. Install logrotate config
sudo cp clamav/shared/clamav-jsonl.conf /etc/logrotate.d/clamav-jsonl

# 4. Reload systemd and enable the timer
sudo systemctl daemon-reload
sudo systemctl enable clamav-scan.timer
sudo systemctl start clamav-scan.timer

# 5. Verify timer is active
sudo systemctl list-timers clamav-scan.timer

# 6. (Optional) Run a manual test now
sudo systemctl start clamav-scan.service

# 7. Check results
cat /var/log/clamav/clamscan.jsonl | python3 -m json.tool
journalctl -u clamav-scan.service --since today
```

---

## 📥 SIEM Ingestion Strategy

### The Problem: How Does Each New Scan Reach the SIEM?

There are **3 layers** working together to ensure no scan result is lost:

```
┌──────────────────────────────────────────────────────┐
│                   Daily Scan Runs                     │
│            (systemd timer → service)                  │
└──────────────┬───────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────┐
│         clamscan-to-json.py writes to:                │
│                                                       │
│   1. stdout → systemd journal (always captured)       │
│   2. /var/log/clamav/clamscan.jsonl (append mode)     │
└──────────────┬───────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────────────────┐
│          SIEM picks it up via ONE of:                  │
│                                                       │
│   Option A: Filebeat/Fluentd tails the JSONL file     │
│   Option B: journalctl → syslog → SIEM forwarder     │
│   Option C: rsyslog imjournal module reads journal    │
└──────────────────────────────────────────────────────┘
```

### Why JSONL Append (Not Overwrite)?

| Approach | Pros | Cons |
|----------|------|------|
| ✅ **Append to JSONL** | History preserved, SIEM can tail it, simple rotation with logrotate | File grows (mitigated by rotation) |
| ❌ Overwrite single file | Small, fixed size | Previous scan lost if SIEM didn't read it yet |
| ❌ Timestamped files | No overwrite risk | Need cleanup, harder for SIEM to track |
| ❌ Send to syslog only | No file management | Depends on syslog being up, no local backup |

### Logrotate Config: `clamav-jsonl.conf`

Keeps 30 days of scan history, compressed:

```
/var/log/clamav/clamscan.jsonl {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0640 root clamupdate
}
```

### SIEM Integration Options

#### Option A: Filebeat (Recommended)

```yaml
# /etc/filebeat/filebeat.yml
filebeat.inputs:
- type: log
  enabled: true
  paths:
    - /var/log/clamav/clamscan.jsonl
  json.keys_under_root: true
  json.add_error_key: true
  fields:
    log_type: clamav_scan

output.elasticsearch:
  hosts: ["your-siem:9200"]
  index: "clamav-scans-%{+yyyy.MM.dd}"
```

#### Option B: journalctl → SIEM

```bash
# One-shot export of today's scan
journalctl -u clamav-scan.service --since today --output cat >> /var/log/clamav/clamscan.jsonl
```

#### Option C: rsyslog

```
# /etc/rsyslog.d/clamav-to-siem.conf
module(load="imjournal" StateFile="imjournal.state")

template(name="ClamAVJSON" type="string" string="%msg%\n")

if $programname == "clamav-scan.service" then {
    action(type="omfwd" target="siem.example.com" port="514" protocol="tcp" template="ClamAVJSON")
}
```

---

## 🔍 Manual Checks with jq

After scans have run and populated `/var/log/clamav/clamscan.jsonl`, use `jq` for ad-hoc analysis.

### Install jq

```bash
# AlmaLinux 9 / Amazon Linux 2
sudo dnf install -y jq      # or: sudo yum install -y jq

# Amazon Linux 2023
sudo dnf install -y jq
```

### 📋 Quick Reference

#### 🟢 Pretty-print the most recent scan

```bash
tail -1 /var/log/clamav/clamscan.jsonl | jq .
```

**Example output:**
```json
{
  "file_results": [
    { "file": "/etc/hostname", "status": "OK" },
    { "file": "/etc/hosts", "status": "OK" },
    { "file": "/etc/passwd", "status": "OK" },
    { "file": "/etc/resolv.conf", "status": "OK" }
  ],
  "scan_summary": {
    "known_viruses": 3627837,
    "engine_version": "1.5.2",
    "scanned_directories": 0,
    "scanned_files": 4,
    "infected_files": 0,
    "data_scanned": "0.00 MB",
    "data_read": "0.00 MB (ratio 0.00:1)",
    "time": "7.349 sec (0 m 7 s)",
    "start_date": "2026:04:22 10:11:37",
    "end_date": "2026:04:22 10:11:45"
  },
  "hostname": "server01",
  "timestamp": "2026-04-22T10:11:45Z"
}
```

#### 🔴 Find all scans with infected files (alerts)

```bash
jq 'select(.scan_summary.infected_files > 0)' /var/log/clamav/clamscan.jsonl
```

**Example output (if a threat was found):**
```json
{
  "file_results": [
    { "file": "/tmp/eicar.com", "status": "FOUND Eicar-Test-Signature" }
  ],
  "scan_summary": {
    "known_viruses": 3627837,
    "engine_version": "1.5.2",
    "scanned_files": 4,
    "infected_files": 1
  },
  "hostname": "server01",
  "timestamp": "2026-04-24T11:03:44Z"
}
```

#### 🔎 List only the infected files across all scans

```bash
jq -r '.file_results[] | select(.status != "OK") | "\(.file) → \(.status)"' /var/log/clamav/clamscan.jsonl
```

**Example output:**
```
/tmp/eicar.com → FOUND Eicar-Test-Signature
/var/www/uploads/shell.php → FOUND Php.Backdoor.Shell-177
```

#### 📊 Summary table: date, files scanned, infected

```bash
jq -r '[.timestamp[:10], .scan_summary.scanned_files, .scan_summary.infected_files, .hostname] | @tsv' /var/log/clamav/clamscan.jsonl | column -t -s $'\t'
```

**Example output:**
```
2026-04-22  4      0  server01
2026-04-23  12483  0  server01
2026-04-24  12483  1  server01
2026-04-25  12483  0  server01
```

#### ⏱️ Extract scan duration per day

```bash
jq -r '"\(.timestamp[:10])  \(.scan_summary.time)"' /var/log/clamav/clamscan.jsonl
```

**Example output:**
```
2026-04-22  7.349 sec (0 m 7 s)
2026-04-23  342.120 sec (5 m 42 s)
2026-04-24  338.502 sec (5 m 38 s)
```

#### 🖥️ Get unique hostnames that have reported scans

```bash
jq -r '.hostname' /var/log/clamav/clamscan.jsonl | sort -u
```

**Example output:**
```
proxy-east-01
webserver-01
webserver-02
```

#### 📈 Count total scans, total infected files

```bash
jq -s '{total_scans: length, total_infected: map(.scan_summary.infected_files // 0) | add}' /var/log/clamav/clamscan.jsonl
```

**Example output:**
```json
{
  "total_scans": 30,
  "total_infected": 3
}
```

#### 🧹 Filter scans by date range

```bash
# Scans from April 2026 only
jq 'select(.timestamp >= "2026-04-01" and .timestamp < "2026-05-01")' /var/log/clamav/clamscan.jsonl
```

#### 🔍 Check engine version across all scans

```bash
jq -r '[.timestamp[:10], .scan_summary.engine_version, .scan_summary.known_viruses] | @tsv' /var/log/clamav/clamscan.jsonl | column -t -s $'\t'
```

**Example output:**
```
2026-04-22  1.5.2  3627837
2026-04-23  1.4.3  3627837
2026-04-24  1.5.2  3627837
```

> 💡 Useful for verifying that all hosts updated to the latest engine version after a ClamAV upgrade.

---

## 📁 File Inventory

```
clamav/                               ← This directory (within linux-security-scanners/)
├── README.md                          ← This file
├── shared/
│   ├── clamscan-to-json.py            ← Production parser (pipes from clamscan, appends JSONL)
│   ├── clamav-scan.service            ← Systemd service definition
│   ├── clamav-scan.timer              ← Systemd timer (daily, randomized 24h)
│   ├── clamav-jsonl.conf              ← Logrotate config for the JSONL file
│   └── parse_to_json.py               ← Original test parser (not used in production)
├── almalinux9/
│   ├── Dockerfile                     ← AlmaLinux 9 + ClamAV 1.5.2 (Cisco Talos RPM)
│   └── results/                       ← Test outputs (gitignored)
├── amazonlinux2/
│   └── Dockerfile                     ← Amazon Linux 2 + ClamAV 1.4.3 (EPEL)
└── amazonlinux2023/
    └── Dockerfile                     ← Amazon Linux 2023 + ClamAV 1.5.2 (Cisco Talos RPM)
```

---

## 🚀 Step-by-Step Reproduction

### Prerequisites

- Windows 11 with Docker Desktop running
- Git Bash or PowerShell terminal
- All commands run from the `linux-security-scanners/` project root

### Step 1: Build All Base Images

```bash
cd linux-security-scanners

docker build -t almalinux9-clamav:latest -f clamav/almalinux9/Dockerfile .
docker build -t amazonlinux2-clamav:latest -f clamav/amazonlinux2/Dockerfile .
docker build -t amazonlinux2023-clamav:latest -f clamav/amazonlinux2023/Dockerfile .
```

### Step 2: Verify Images

```bash
docker run --rm almalinux9-clamav:latest clamscan --version
docker run --rm amazonlinux2-clamav:latest clamscan --version
docker run --rm amazonlinux2023-clamav:latest clamscan --version
```

Expected output:
```
ClamAV 1.5.2/27979/...   # AlmaLinux 9
ClamAV 1.4.3/27979/...   # Amazon Linux 2
ClamAV 1.5.2/27979/...   # Amazon Linux 2023
```

### Step 3: Test Raw Output Comparison

```bash
docker run --rm almalinux9-clamav:latest bash -c '
  echo "=== WITH summary ==="
  clamscan /etc/hostname /etc/hosts /etc/passwd
  echo ""
  echo "=== WITHOUT summary ==="
  clamscan --no-summary /etc/hostname /etc/hosts /etc/passwd
'
```

### Step 4: Test JSON Conversion

```bash
docker run --rm almalinux9-clamav:latest bash -c '
  mkdir -p /var/log/clamav
  clamscan /etc/hostname /etc/hosts | python3 /usr/local/bin/clamscan-to-json.py
'
```

### Step 5: Test JSONL Append (Multiple Scans)

```bash
docker run --rm almalinux9-clamav:latest bash -c '
  mkdir -p /var/log/clamav
  echo "Scan 1:"; clamscan /etc/hostname | python3 /usr/local/bin/clamscan-to-json.py
  echo "Scan 2:"; clamscan /etc/hosts /etc/passwd | python3 /usr/local/bin/clamscan-to-json.py
  echo "Scan 3:"; clamscan --no-summary /etc/resolv.conf | python3 /usr/local/bin/clamscan-to-json.py
  echo ""
  echo "JSONL file:"
  cat /var/log/clamav/clamscan.jsonl
  echo ""
  echo "Line count: $(wc -l < /var/log/clamav/clamscan.jsonl)"
'
```

### Step 6: Test All Three OS Images

```bash
for img in almalinux9-clamav amazonlinux2-clamav amazonlinux2023-clamav; do
  echo "===== $img ====="
  docker run --rm $img bash -c '
    mkdir -p /var/log/clamav
    clamscan /etc/hostname /etc/hosts /etc/passwd | python3 /usr/local/bin/clamscan-to-json.py
    echo ""
    echo "JSONL:"
    cat /var/log/clamav/clamscan.jsonl | tail -1 | python3 -m json.tool
  '
  echo ""
done
```

### Step 7: Deploy on Production Host

```bash
# Copy scripts and systemd files
sudo cp clamav/shared/clamscan-to-json.py /usr/local/bin/
sudo chmod +x /usr/local/bin/clamscan-to-json.py
sudo cp clamav/shared/clamav-scan.service /etc/systemd/system/
sudo cp clamav/shared/clamav-scan.timer /etc/systemd/system/
sudo cp clamav/shared/clamav-jsonl.conf /etc/logrotate.d/

# Create log directory
sudo mkdir -p /var/log/clamav
sudo touch /var/log/clamav/clamscan.jsonl
sudo chmod 640 /var/log/clamav/clamscan.jsonl

# Install jq for manual checks
sudo dnf install -y jq    # or: sudo yum install -y jq

# Enable and start timer
sudo systemctl daemon-reload
sudo systemctl enable --now clamav-scan.timer

# Verify
sudo systemctl list-timers clamav-scan.timer
sudo systemctl start clamav-scan.service   # manual test
tail -1 /var/log/clamav/clamscan.jsonl | jq .
```

---

## 🧹 Cleanup

```bash
# Remove Docker images
docker rmi almalinux9-clamav:latest amazonlinux2-clamav:latest amazonlinux2023-clamav:latest

# Remove base images
docker rmi almalinux:9 amazonlinux:2 amazonlinux:2023

# Remove the project directory
rm -rf linux-security-scanners/
```
