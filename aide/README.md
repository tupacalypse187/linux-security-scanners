# 🔒 AIDE File Integrity Scanner: Complete Guide

> AlmaLinux 9 · Amazon Linux 2 · Amazon Linux 2023 · JSON Output · Systemd Timer · SIEM Ingestion

---

## 📋 Table of Contents

- [🔍 What Was Discovered](#-what-was-discovered)
- [🐧 OS-Specific Findings](#-os-specific-findings)
- [📊 AIDE Output Comparison](#-aide-output-comparison)
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
| **AIDE Versions** | 0.16 (AlmaLinux 9) · 0.16.2 (Amazon Linux 2) · 0.18.6 (Amazon Linux 2023) |
| **`--json` CLI flag** | ❌ **Does not exist** in any version |
| **`report_format=json` config** | ⚠️ Documented in AIDE 0.18 man page (`aide.conf(5)`) but accepted without effect in the AL2023 build — still outputs plain text |
| **Python parser required** | ✅ All three OSes need the `aide-to-json.py` wrapper to produce JSON |
| **AIDE workflow** | `aide --init` (baseline) → `aide --check` (compare) → `aide --update` (refresh baseline) |
| **Docker Desktop** | ✅ All testing done on Windows 11 Docker Desktop |

### Key Difference from ClamAV

AIDE is **stateful** — it requires a baseline database to compare against. The Docker images bake in an initialized database at build time. In production, you init once and then check/update periodically.

---

## 🐧 OS-Specific Findings

### Comparison Matrix

| Feature | 🎩 AlmaLinux 9 | 📦 Amazon Linux 2 | ☁️ Amazon Linux 2023 |
|---------|----------------|-------------------|---------------------|
| **AIDE Version** | 0.16 | 0.16.2 | 0.18.6 |
| **Install Method** | `dnf install aide` | `yum install aide` | `dnf install aide` |
| **Config Location** | `/etc/aide.conf` | `/etc/aide.conf` | `/etc/aide.conf` |
| **Database Location** | `/var/lib/aide/aide.db.gz` | `/var/lib/aide/aide.db.gz` | `/var/lib/aide/aide.db.gz` |
| **Native JSON** | ❌ No | ❌ No | ⚠️ `report_format=json` accepted but non-functional in package build |
| **Hash Algorithms** | SHA512 (default) | SHA256 (default) | SHA256/SHA512 + GOST, Whirlpool, Stribog |
| **Multi-threaded** | No | No | Yes (`--workers=N`) |
| **Build Gotchas** | None | None | None |

### About `report_format=json` on Amazon Linux 2023

The AIDE 0.18.6 man page documents:
```
report_format (type: report format, default: plain, added in AIDE v0.18)
    plain: Print report in plain human-readable format.
    json:  Print report in json machine-readable format.
```

However, in testing the AL2023 package build, setting `report_format=json` in `aide.conf`:
- Does **not** produce a config error (option is recognized)
- Does **not** change the output format (still plain text)

This suggests the JSON reporter was not compiled into the Amazon Linux 2023 package despite the config option being present. All three OSes therefore use the Python parser.

---

## 📊 AIDE Output Comparison

### ✅ Clean Check (no changes)

```
Start timestamp: 2026-04-22 11:13:40 +0000 (AIDE 0.18.6)
AIDE found NO differences between database and filesystem. Looks okay!!

Number of entries:	631
...
End timestamp: 2026-04-22 11:13:40 +0000 (run time: 0m 0s)
```

### 🔴 Check with Changes

```
Start timestamp: 2026-04-22 11:14:20 +0000 (AIDE 0.18.6)
AIDE found differences between database and filesystem!!

Summary:
  Total number of entries:	3
  Added entries:		1
  Removed entries:		1
  Changed entries:		1

---------------------------------------------------
Added entries:
---------------------------------------------------

f++++++++++++++++: /tmp/testdir/file3.txt

---------------------------------------------------
Removed entries:
---------------------------------------------------

f----------------: /tmp/testdir/file2.txt

---------------------------------------------------
Changed entries:
---------------------------------------------------

f = ... ....H    : /tmp/testdir/file1.txt

---------------------------------------------------
Detailed information about changes:
---------------------------------------------------

File: /tmp/testdir/file1.txt
 SHA256    : UWrXs4iy... | UrMnJyH/...

End timestamp: 2026-04-22 11:14:20 +0000 (run time: 0m 0s)
```

### Key Sections

| Section | What It Shows |
|---------|---------------|
| **Summary** | Total entries, added/removed/changed counts |
| **Added entries** | Files not in baseline (`f++++++++++++++++`) |
| **Removed entries** | Files in baseline but now gone (`f----------------`) |
| **Changed entries** | Files with attribute differences (`f = ...H...`) |
| **Detailed changes** | Per-attribute old vs new values (hash, permissions, timestamps) |

---

## ⚙️ JSON Conversion

### Architecture

```
aide -C (check against baseline)
  │
  ▼  (pipe stdout + stderr)
aide-to-json.py
  │
  ├──▶ stdout (captured by systemd journal)
  │
  └──▶ /var/log/aide/aide.jsonl (append, one line per check)
```

### JSON Schema

**Clean run:**
```json
{
  "result": "clean",
  "hostname": "server01",
  "timestamp": "2026-04-22T10:00:00Z",
  "scanner": "aide"
}
```

**Changes detected:**
```json
{
  "result": "changes_detected",
  "summary": {
    "total_entries": 9405,
    "added": 1,
    "removed": 0,
    "changed": 3
  },
  "changed_entries": [
    {"path": "/etc/resolv.conf", "changed_attrs": "...H", "attributes": "f = ..."}
  ],
  "detailed_changes": [
    {"path": "/etc/resolv.conf", "attribute": "Perm", "old": "-rw-r--r--", "new": "-rwxrwxrwx"},
    {"path": "/etc/resolv.conf", "attribute": "SHA256", "old": "BdNg+yp9...", "new": "VTMqVqeh..."}
  ],
  "hostname": "server01",
  "timestamp": "2026-04-22T10:00:00Z",
  "scanner": "aide"
}
```

### SIEM-Ready Single Line

```
{"result":"changes_detected","summary":{"total_entries":9405,"added":0,"removed":0,"changed":3},"detailed_changes":[{"path":"/etc/resolv.conf","attribute":"Perm","old":"-rw-r--r--","new":"-rwxrwxrwx"},...],"hostname":"server01","timestamp":"2026-04-22T10:00:00Z","scanner":"aide"}
```

---

## 🐙 Docker Base Images

### 🎩 AlmaLinux 9

```dockerfile
# aide/almalinux9/Dockerfile
FROM almalinux:9

COPY aide/shared/aide-to-json.py /usr/local/bin/aide-to-json.py

RUN dnf install -y aide python3 \
    && chmod +x /usr/local/bin/aide-to-json.py \
    && aide --init -c /etc/aide.conf \
    && cp /var/lib/aide/aide.db.new.gz /var/lib/aide/aide.db.gz \
    && dnf clean all
```

### 📦 Amazon Linux 2

```dockerfile
# aide/amazonlinux2/Dockerfile
FROM amazonlinux:2

COPY aide/shared/aide-to-json.py /usr/local/bin/aide-to-json.py

RUN yum install -y aide python3 \
    && chmod +x /usr/local/bin/aide-to-json.py \
    && aide --init \
    && cp /var/lib/aide/aide.db.new.gz /var/lib/aide/aide.db.gz \
    && yum clean all
```

### ☁️ Amazon Linux 2023

```dockerfile
# aide/amazonlinux2023/Dockerfile
FROM amazonlinux:2023

COPY aide/shared/aide-to-json.py /usr/local/bin/aide-to-json.py

RUN dnf install -y aide python3 \
    && chmod +x /usr/local/bin/aide-to-json.py \
    && aide --init -c /etc/aide.conf \
    && cp /var/lib/aide/aide.db.new.gz /var/lib/aide/aide.db.gz \
    && dnf clean all
```

### Build All

```bash
# From project root
docker build -t almalinux9-aide:latest -f aide/almalinux9/Dockerfile .
docker build -t amazonlinux2-aide:latest -f aide/amazonlinux2/Dockerfile .
docker build -t amazonlinux2023-aide:latest -f aide/amazonlinux2023/Dockerfile .
```

---

## 🤖 Systemd Service + Timer

### Service: `aide-check.service`

```ini
[Unit]
Description=AIDE File Integrity Check
Documentation=man:aide(1)
After=network-online.target
Wants=network-online.target

[Service]
Type=oneshot
User=root

ExecStart=/bin/bash -c '/usr/sbin/aide -C 2>&1 | /usr/local/bin/aide-to-json.py'
TimeoutStartSec=7200
IOSchedulingClass=idle
CPUSchedulingPolicy=idle

[Install]
WantedBy=multi-user.target
```

### Timer: `aide-check.timer`

Runs daily at 2am with up to 2h random jitter.

```ini
[Unit]
Description=Daily AIDE File Integrity Check Timer

[Timer]
OnCalendar=*-*-* 02:00:00
RandomizedDelaySec=7200
Persistent=true
AccuracySec=1h

[Install]
WantedBy=timers.target
```

### AIDE Init Service (run once after install)

```ini
# /etc/systemd/system/aide-init.service
[Unit]
Description=AIDE Database Initialization
After=network-online.target

[Service]
Type=oneshot
User=root
ExecStart=/usr/sbin/aide --init
ExecStartPost=/bin/bash -c 'cp /var/lib/aide/aide.db.new.gz /var/lib/aide/aide.db.gz'
```

### Install on Host

```bash
# 1. Install AIDE and init the database
sudo dnf install -y aide jq
sudo aide --init
sudo cp /var/lib/aide/aide.db.new.gz /var/lib/aide/aide.db.gz

# 2. Copy shared files
sudo cp aide/shared/aide-to-json.py /usr/local/bin/
sudo chmod +x /usr/local/bin/aide-to-json.py
sudo cp aide/shared/aide-check.service /etc/systemd/system/
sudo cp aide/shared/aide-check.timer /etc/systemd/system/
sudo cp aide/shared/aide-jsonl.conf /etc/logrotate.d/aide-jsonl

# 3. Create log directory
sudo mkdir -p /var/log/aide
sudo touch /var/log/aide/aide.jsonl
sudo chmod 640 /var/log/aide/aide.jsonl

# 4. Enable and start timer
sudo systemctl daemon-reload
sudo systemctl enable --now aide-check.timer

# 5. Verify
sudo systemctl list-timers aide-check.timer
sudo systemctl start aide-check.service   # manual test
tail -1 /var/log/aide/aide.jsonl | jq .
```

---

## 📥 SIEM Ingestion Strategy

Same architecture as ClamAV — JSONL append with logrotate:

```
aide -C 2>&1 | aide-to-json.py
                    │
                    ├──▶ stdout → systemd journal
                    └──▶ /var/log/aide/aide.jsonl (append)
                              │
                              ▼
                    Filebeat / Fluentd / rsyslog → SIEM
```

### Filebeat Config

```yaml
filebeat.inputs:
- type: log
  enabled: true
  paths:
    - /var/log/aide/aide.jsonl
  json.keys_under_root: true
  json.add_error_key: true
  fields:
    log_type: aide_check

output.elasticsearch:
  hosts: ["your-siem:9200"]
  index: "aide-checks-%{+yyyy.MM.dd}"
```

### Logrotate

```
# /etc/logrotate.d/aide-jsonl
/var/log/aide/aide.jsonl {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0640 root root
}
```

---

## 🔍 Manual Checks with jq

### 🟢 Pretty-print the most recent check

```bash
tail -1 /var/log/aide/aide.jsonl | jq .
```

**Example output:**
```json
{
  "result": "changes_detected",
  "summary": { "total_entries": 9405, "added": 0, "removed": 0, "changed": 3 },
  "detailed_changes": [
    { "path": "/etc/resolv.conf", "attribute": "Perm", "old": "-rw-r--r--", "new": "-rwxrwxrwx" }
  ],
  "hostname": "server01",
  "timestamp": "2026-04-22T10:00:00Z",
  "scanner": "aide"
}
```

### 🔴 Find all checks that detected changes

```bash
jq 'select(.result == "changes_detected")' /var/log/aide/aide.jsonl
```

### 🔎 List unique changed file paths across all checks

```bash
jq -r '.detailed_changes[]?.path' /var/log/aide/aide.jsonl | sort -u
```

**Example output:**
```
/etc/resolv.conf
/etc/ssh/sshd_config
/var/www/html/index.html
```

### 📊 Summary table: date, changes, status

```bash
jq -r '[.timestamp[:10], .result, (.summary.changed // 0), (.summary.added // 0), (.summary.removed // 0)] | @tsv' /var/log/aide/aide.jsonl | column -t -s $'\t'
```

**Example output:**
```
2026-04-22  changes_detected  3  0  0
2026-04-23  clean             0  0  0
2026-04-24  changes_detected  5  1  0
2026-04-25  clean             0  0  0
```

### 🔐 Show only permission changes

```bash
jq 'select(.detailed_changes[]?.attribute == "Perm")' /var/log/aide/aide.jsonl
```

### 🔑 Show only hash changes (potential file tampering)

```bash
jq -r '.detailed_changes[] | select(.attribute | test("SHA|MD5")) | "\(.path) \(.attribute) changed"' /var/log/aide/aide.jsonl | sort -u
```

**Example output:**
```
/etc/resolv.conf SHA256 changed
/etc/ssh/sshd_config SHA512 changed
```

### 📈 Count total changes over time

```bash
jq -s '{total_checks: length, with_changes: map(select(.result == "changes_detected")) | length, total_changed_files: [.[].detailed_changes[]?.path] | unique | length}' /var/log/aide/aide.jsonl
```

**Example output:**
```json
{
  "total_checks": 30,
  "with_changes": 5,
  "total_changed_files": 12
}
```

### 🧹 Filter by date range

```bash
jq 'select(.timestamp >= "2026-04-01" and .timestamp < "2026-05-01")' /var/log/aide/aide.jsonl
```

### 🖥️ Get unique hostnames that have reported

```bash
jq -r '.hostname' /var/log/aide/aide.jsonl | sort -u
```

### 🔔 Alert: any file in /etc changed

```bash
jq 'select(.detailed_changes[]?.path | startswith("/etc")) | {timestamp, hostname, changed: [.detailed_changes[]?.path | select(startswith("/etc"))] | unique}' /var/log/aide/aide.jsonl
```

---

## 📁 File Inventory

```
aide/
├── README.md                     ← This file
├── shared/
│   ├── aide-to-json.py           ← Production parser (pipes from aide, appends JSONL)
│   ├── aide-check.service        ← Systemd service definition
│   ├── aide-check.timer          ← Systemd timer (daily, 2am + 2h jitter)
│   └── aide-jsonl.conf           ← Logrotate config
├── almalinux9/
│   └── Dockerfile                ← AlmaLinux 9 + AIDE 0.16
├── amazonlinux2/
│   └── Dockerfile                ← Amazon Linux 2 + AIDE 0.16.2
└── amazonlinux2023/
    └── Dockerfile                ← Amazon Linux 2023 + AIDE 0.18.6
```

---

## 🚀 Step-by-Step Reproduction

### Prerequisites

- Windows 11 with Docker Desktop
- Git Bash or PowerShell

### Step 1: Build All Images

```bash
cd linux-security-scanners

docker build -t almalinux9-aide:latest -f aide/almalinux9/Dockerfile .
docker build -t amazonlinux2-aide:latest -f aide/amazonlinux2/Dockerfile .
docker build -t amazonlinux2023-aide:latest -f aide/amazonlinux2023/Dockerfile .
```

### Step 2: Verify Versions

```bash
docker run --rm almalinux9-aide:latest aide --version       # Aide 0.16
docker run --rm amazonlinux2-aide:latest aide --version      # Aide 0.16.2
docker run --rm amazonlinux2023-aide:latest aide --version   # Aide 0.18.6
```

### Step 3: Test Clean Check

```bash
docker run --rm almalinux9-aide:latest bash -c '
  mkdir -p /var/log/aide
  aide -C 2>&1 | python3 /usr/local/bin/aide-to-json.py | python3 -m json.tool
'
```

### Step 4: Test with Induced Changes

```bash
docker run --rm almalinux9-aide:latest bash -c '
  mkdir -p /var/log/aide
  echo "tampered" > /tmp/hack
  chmod 777 /etc/resolv.conf
  aide -C 2>&1 | python3 /usr/local/bin/aide-to-json.py | python3 -m json.tool
'
```

### Step 5: Test JSONL Append

```bash
docker run --rm almalinux9-aide:latest bash -c '
  mkdir -p /var/log/aide
  aide -C 2>&1 | python3 /usr/local/bin/aide-to-json.py
  echo "tampered" > /tmp/hack
  aide -C 2>&1 | python3 /usr/local/bin/aide-to-json.py
  echo "Lines: $(wc -l < /var/log/aide/aide.jsonl)"
  cat /var/log/aide/aide.jsonl
'
```

### Step 6: Deploy on Production Host

```bash
sudo dnf install -y aide jq
sudo aide --init
sudo cp /var/lib/aide/aide.db.new.gz /var/lib/aide/aide.db.gz

sudo cp aide/shared/aide-to-json.py /usr/local/bin/
sudo chmod +x /usr/local/bin/aide-to-json.py
sudo cp aide/shared/aide-check.service /etc/systemd/system/
sudo cp aide/shared/aide-check.timer /etc/systemd/system/
sudo cp aide/shared/aide-jsonl.conf /etc/logrotate.d/

sudo mkdir -p /var/log/aide
sudo touch /var/log/aide/aide.jsonl

sudo systemctl daemon-reload
sudo systemctl enable --now aide-check.timer
sudo systemctl start aide-check.service   # manual test
tail -1 /var/log/aide/aide.jsonl | jq .
```

---

## 🧹 Cleanup

```bash
docker rmi almalinux9-aide:latest amazonlinux2-aide:latest amazonlinux2023-aide:latest
docker rmi almalinux:9 amazonlinux:2 amazonlinux:2023
```
