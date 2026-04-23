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
| **`report_format=json` config (AL2023)** | ✅ **Works** — produces valid JSON, but is **order-sensitive** (see below) |
| **`report_format=json` config (AL9, AL2)** | ❌ Option does not exist in AIDE 0.16 / 0.16.2 — produces `Configuration error: unknown expression` |
| **Python parser required** | ✅ AlmaLinux 9 and Amazon Linux 2 need the `aide-to-json.py` wrapper · AL2023 can use either native JSON or the parser |
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
| **Native JSON** | ❌ No | ❌ No | ✅ `report_format=json` works (order-sensitive in config — see below) |
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

**The JSON reporter is fully functional in the AL2023 package.** It is, however, **order-sensitive** in the config — which is easy to miss and which tripped up an earlier version of this document.

#### The gotcha

AIDE applies `report_format` to each `report_url` **at the moment the URL is declared**, not globally. The default `/etc/aide.conf` on AL2023 declares its two `report_url=` lines early (around line 21–22):

```
report_url=file:@@{LOGDIR}/aide.log
report_url=stdout
```

If you **append** `report_format=json` to the end of the file, it arrives *after* both URLs have already been bound to the default `plain` format — so the scan still prints plain text and you'd conclude (wrongly) that the feature is broken.

#### What actually works

| Approach | Result |
|---|---|
| `aide --check -B 'report_format=json'` on the CLI | ✅ JSON |
| `report_format=json` inserted **before** `report_url=` lines in `aide.conf` | ✅ JSON |
| `report_format=json` **appended** to the end of `aide.conf` | ❌ Plain text (silent failure) |
| `report_url=stdout?report_format=json` per-URL query string | ❌ `unknown URL-type` error |

#### Why we still ship the Python parser

Even though AL2023 can produce native JSON, the Python parser remains the recommended pipeline because:

1. **Uniform schema across all three OSes** — AlmaLinux 9 and Amazon Linux 2 run AIDE 0.16 / 0.16.2 which have no JSON support at all (the `report_format` expression is unknown). The parser normalises output into one SIEM-friendly shape regardless of source OS.
2. **Host-enriched fields** — the parser adds `hostname`, `timestamp`, and `scanner` fields that the native AIDE JSON does not emit.
3. **JSONL (one object per line)** — native JSON is pretty-printed and multi-line, which defeats line-oriented log shippers. The parser emits a single JSON object per check.

See [`aide/amazonlinux2023/native-json-demo.sh`](amazonlinux2023/native-json-demo.sh) for a runnable A/B reproducer showing the working and broken config orderings.

See [`aide/amazonlinux2023/native-json-comparison.md`](amazonlinux2023/native-json-comparison.md) for a detailed side-by-side comparison of native JSON vs Python wrapper output with schema analysis and recommendations.

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
  "outline": "AIDE found NO differences between database and filesystem. Looks okay!!",
  "run_time_seconds": 2,
  "hostname": "server01",
  "timestamp": "2026-04-22T10:00:00Z",
  "scanner": "aide"
}
```

**Changes detected:**
```json
{
  "result": "changes_detected",
  "outline": "AIDE found differences between database and filesystem!!",
  "summary": {
    "total_entries": 9405,
    "added": 1,
    "removed": 0,
    "changed": 3
  },
  "added_entries": [
    {"path": "/tmp/hack", "flags": "f++++++++++++++++"}
  ],
  "changed_entries": [
    {"path": "/etc/resolv.conf", "flags": "f > p..    .CA."}
  ],
  "detailed_changes": [
    {"path": "/etc/resolv.conf", "attribute": "Perm", "old": "-rw-r--r--", "new": "-rwxrwxrwx"},
    {"path": "/etc/resolv.conf", "attribute": "SHA256", "old": "BdNg+yp9...", "new": "VTMqVqeh..."}
  ],
  "databases": {
    "/var/lib/aide/aide.db.gz": {
      "SHA256": "uEopVGfy1zOtO9CMFLDoSmY2t11YlRYd4YnblD09B20=",
      "SHA512": "EhbGN6a8y8qMRLCPC0xGPe35c1p4u31l..."
    }
  },
  "run_time_seconds": 3,
  "hostname": "server01",
  "timestamp": "2026-04-22T10:00:00Z",
  "scanner": "aide"
}
```

Empty collections (`added_entries`, `removed_entries`, `changed_entries`, `databases`) and unset fields (`outline`, `run_time_seconds`) are omitted from the output.

### Field Reference

| Field | Type | Description |
|-------|------|-------------|
| `result` | string | `"clean"` or `"changes_detected"` |
| `outline` | string | AIDE's status message (e.g. "AIDE found differences between database and filesystem!!") |
| `summary` | object | Entry counts: `total_entries`, `added`, `removed`, `changed` |
| `added_entries` | array | Files not in baseline: `{"path": "...", "flags": "f++++++++++++++++"}` |
| `removed_entries` | array | Files in baseline but now gone: `{"path": "...", "flags": "f----------------"}` |
| `changed_entries` | array | Files with attribute differences: `{"path": "...", "flags": "f > p..    .CA."}` |
| `detailed_changes` | array | Per-attribute old vs new: `{"path": "...", "attribute": "Perm", "old": "...", "new": "..."}` |
| `databases` | object | AIDE database integrity hashes keyed by DB path, then by algorithm |
| `run_time_seconds` | integer | Scan duration in seconds |
| `hostname` | string | System hostname (added by parser) |
| `timestamp` | string | ISO 8601 UTC timestamp (added by parser) |
| `scanner` | string | Always `"aide"` (added by parser) |

### SIEM-Ready Single Line

```
{"result":"changes_detected","outline":"AIDE found differences...","summary":{"total_entries":9405,"added":1,"removed":0,"changed":3},"added_entries":[{"path":"/tmp/hack","flags":"f++++++++++++++++"}],"changed_entries":[{"path":"/etc/resolv.conf","flags":"f > p..    .CA."}],"detailed_changes":[{"path":"/etc/resolv.conf","attribute":"Perm","old":"-rw-r--r--","new":"-rwxrwxrwx"},...],"databases":{"/var/lib/aide/aide.db.gz":{"SHA256":"...","SHA512":"..."}},"run_time_seconds":3,"hostname":"server01","timestamp":"2026-04-22T10:00:00Z","scanner":"aide"}
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

Runs every 4 hours with up to 30 minutes random jitter.

```ini
[Unit]
Description=AIDE File Integrity Check Timer (every 4 hours)

[Timer]
OnCalendar=*-*-* 00/4:00:00
RandomizedDelaySec=1800
Persistent=true
AccuracySec=5m

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
  "outline": "AIDE found differences between database and filesystem!!",
  "summary": { "total_entries": 9405, "added": 1, "removed": 0, "changed": 3 },
  "added_entries": [
    { "path": "/tmp/hack", "flags": "f++++++++++++++++" }
  ],
  "changed_entries": [
    { "path": "/etc/resolv.conf", "flags": "f > p..    .CA." }
  ],
  "detailed_changes": [
    { "path": "/etc/resolv.conf", "attribute": "Perm", "old": "-rw-r--r--", "new": "-rwxrwxrwx" }
  ],
  "databases": {
    "/var/lib/aide/aide.db.gz": { "SHA256": "uEopVGfy...", "SHA512": "EhbGN6a8..." }
  },
  "run_time_seconds": 3,
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

### 📄 List added files across all checks

```bash
jq -r '.added_entries[]?.path' /var/log/aide/aide.jsonl | sort -u
```

### 🏷️ Show AIDE flag strings for changed files

```bash
jq -r '.changed_entries[]? | "\(.flags) \(.path)"' /var/log/aide/aide.jsonl
```

**Example output:**
```
f > p..    .CA. /etc/resolv.conf
f   ...    .C.. /etc/hosts
```

### 📊 Summary table: date, changes, status

```bash
jq -r '[.timestamp[:10], .result, (.summary.changed // 0), (.summary.added // 0), (.summary.removed // 0), (.run_time_seconds // "-")] | @tsv' /var/log/aide/aide.jsonl | column -t -s $'\t'
```

**Example output:**
```
2026-04-22  changes_detected  3  1  0  3
2026-04-23  clean             0  0  0  2
2026-04-24  changes_detected  5  1  0  4
2026-04-25  clean             0  0  0  2
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

### 🗄️ Show database integrity hashes

```bash
jq '.databases' /var/log/aide/aide.jsonl
```

### ⏱️ Track scan duration over time

```bash
jq -r '[.timestamp[:10], .run_time_seconds] | @tsv' /var/log/aide/aide.jsonl | column -t -s $'\t'
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
│   ├── aide-check.timer          ← Systemd timer (every 4 hours, 30m jitter)
│   └── aide-jsonl.conf           ← Logrotate config
├── almalinux9/
│   ├── Dockerfile                ← AlmaLinux 9 + AIDE 0.16
│   └── results/                  ← Sample test outputs
│       ├── aide.log              ←   Raw output: clean + tampered check
│       └── aide.json             ←   JSON output: compact + pretty-printed
├── amazonlinux2/
│   ├── Dockerfile                ← Amazon Linux 2 + AIDE 0.16.2
│   └── results/                  ← Sample test outputs
└── amazonlinux2023/
    ├── Dockerfile                ← Amazon Linux 2023 + AIDE 0.18.6
    ├── results/                  ← Sample test outputs
    ├── native-json-comparison.md ← Native JSON vs wrapper analysis
    └── native-json-demo.sh       ← report_format=json reproducer script
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
