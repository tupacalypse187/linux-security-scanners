# Linux Security Scanners — Test Results Breakdown

> Generated: 2026-04-24 | Platform: Windows 11 x86 (Docker Desktop)
> Images: 6 built, 6 tested — all passing

---

## Table of Contents

- [Test Environment](#test-environment)
- [Image Inventory](#image-inventory)
- [Section 1: ClamAV Results](#section-1-clamav-results)
  - [How ClamAV Tests Work](#how-clamav-tests-work)
  - [AlmaLinux 9](#clamav--almalinux-9)
  - [Amazon Linux 2](#clamav--amazon-linux-2)
  - [Amazon Linux 2023](#clamav--amazon-linux-2023)
  - [ClamAV Cross-OS Comparison](#clamav-cross-os-comparison)
- [Section 2: AIDE Results](#section-2-aide-results)
  - [How AIDE Tests Work](#how-aide-tests-work)
  - [Important: Why "Clean" Checks Show Changes](#important-why-clean-checks-show-changes)
  - [AlmaLinux 9](#aide--almalinux9)
  - [Amazon Linux 2](#aide--amazon-linux-2)
  - [Amazon Linux 2023](#aide--amazonlinux-2023)
  - [AIDE Cross-OS Comparison](#aide-cross-os-comparison)
- [Section 3: JSONL Append Validation](#section-3-jsonl-append-validation)
- [Section 4: File Inventory](#section-4-file-inventory)

---

## Test Environment

| Item | Value |
|------|-------|
| Host OS | Windows 11 Pro (Docker Desktop) |
| Test Date | 2026-04-24 |
| Files scanned (ClamAV) | \`/etc/hostname\`, \`/etc/hosts\`, \`/etc/passwd\`, \`/etc/resolv.conf\` |
| Tamper test (AIDE) | \`echo "tampered" > /tmp/ci-test-hack\` + \`chmod 777 /etc/resolv.conf\` |

---

## Image Inventory

| Image Tag | Scanner | Version | Base Image | Install Source |
|-----------|---------|---------|------------|----------------|
| `almalinux9-clamav:latest    ` | ClamAV | 1.5.2   | almalinux9      | Cisco Talos RPM  |
| `amazonlinux2-clamav:latest  ` | ClamAV | 1.4.3   | amazonlinux:2   | EPEL             |
| `amazonlinux2023-clamav:latest` | ClamAV | 1.5.2   | amazonlinux:2023 | Cisco Talos RPM  |
| `almalinux9-aide:latest      ` | AIDE   | 0.16    | almalinux9      | dnf/yum (distro) |
| `amazonlinux2-aide:latest    ` | AIDE   | 0.16.2  | amazonlinux:2   | dnf/yum (distro) |
| `amazonlinux2023-aide:latest ` | AIDE   | 0.18.6  | amazonlinux:2023 | dnf/yum (distro) |

---

## Section 1: ClamAV Results

### How ClamAV Tests Work

Each image runs two scans:

1. **WITH summary** (default) — `clamscan /etc/hostname /etc/hosts /etc/passwd /etc/resolv.conf`
   - Produces per-file results (`OK` or `FOUND <virus-name>`) plus a `SCAN SUMMARY` block
   - The JSON parser captures both `file_results` and `scan_summary`
2. **WITHOUT summary** — `clamscan --no-summary /etc/hostname /etc/hosts /etc/passwd /etc/resolv.conf`
   - Produces only per-file results; the summary block is suppressed entirely
   - The JSON parser captures only `file_results` (no `scan_summary` key)

Both scans are piped through `clamscan-to-json.py` which produces one JSON line per scan and appends to `/var/log/clamav/clamscan.jsonl`.

The `--json` flag is **not available** in any of these builds (neither EPEL nor Cisco Talos RPM compiles it in), which is why the Python parser exists.
### ClamAV — AlmaLinux 9

**File:** `clamav/almalinux9/clamscan.log`

| Field | Value |
|-------|-------|
| Engine | ClamAV 1.5.2 |
| Signatures | 3627837 |
| Files scanned | 4 |
| Infected files | 0 |
| Scan time | 8.852 sec (0 m 8 s) |
| Data scanned | 2.26 KiB |

**Key observations:**

- All 4 files returned `OK` — no threats detected (expected for system config files)
- The `WITH summary` section includes the full `SCAN SUMMARY` block
- The `WITHOUT summary` section shows only per-file results — no summary block

**File:** `clamav/almalinux9/clamscan.json` — 2 JSON lines

| Section | What it shows |
|---------|---------------|
| `WITH summary (1 JSON line)` | `file_results` array + `scan_summary` object + `hostname` + `timestamp` |
| `WITHOUT summary (1 JSON line)` | `file_results` only + `hostname` + `timestamp` — no `scan_summary` |
| `JSONL file (2 scans appended)` | Proves one-line-per-scan JSONL append |

### ClamAV — Amazon Linux 2

**File:** `clamav/amazonlinux2/clamscan.log`

| Field | Value |
|-------|-------|
| Engine | ClamAV 1.4.3 |
| Signatures | 3627837 |
| Files scanned | 4 |
| Infected files | 0 |
| Scan time | 14.552 sec (0 m 14 s) |
| Data scanned | 0.00 MB |

**Key observations:**

- All 4 files returned `OK` — no threats detected (expected for system config files)
- The `WITH summary` section includes the full `SCAN SUMMARY` block
- The `WITHOUT summary` section shows only per-file results — no summary block
- **Slower scan** than the other OSes — ClamAV 1.4.3 on older glibc 2.26 is noticeably slower
- `data_scanned` reports `0.00 MB` (older format) vs newer KiB format on 1.5.2

**File:** `clamav/amazonlinux2/clamscan.json` — 2 JSON lines

| Section | What it shows |
|---------|---------------|
| `WITH summary (1 JSON line)` | `file_results` array + `scan_summary` object + `hostname` + `timestamp` |
| `WITHOUT summary (1 JSON line)` | `file_results` only + `hostname` + `timestamp` — no `scan_summary` |
| `JSONL file (2 scans appended)` | Proves one-line-per-scan JSONL append |

### ClamAV — Amazon Linux 2023

**File:** `clamav/amazonlinux2023/clamscan.log`

| Field | Value |
|-------|-------|
| Engine | ClamAV 1.5.2 |
| Signatures | 3627837 |
| Files scanned | 4 |
| Infected files | 0 |
| Scan time | 8.224 sec (0 m 8 s) |
| Data scanned | 1.92 KiB |

**Key observations:**

- All 4 files returned `OK` — no threats detected (expected for system config files)
- The `WITH summary` section includes the full `SCAN SUMMARY` block
- The `WITHOUT summary` section shows only per-file results — no summary block

**File:** `clamav/amazonlinux2023/clamscan.json` — 2 JSON lines

| Section | What it shows |
|---------|---------------|
| `WITH summary (1 JSON line)` | `file_results` array + `scan_summary` object + `hostname` + `timestamp` |
| `WITHOUT summary (1 JSON line)` | `file_results` only + `hostname` + `timestamp` — no `scan_summary` |
| `JSONL file (2 scans appended)` | Proves one-line-per-scan JSONL append |

### ClamAV Cross-OS Comparison

| Metric | AL9 | AL2 | AL2023 |
|--------|-----|-----|--------|
| Version | 1.5.2 | 1.4.3 | 1.5.2 |
| Signatures | 3627837 | 3627837 | 3627837 |
| Scan time | 8.852 sec (0 m 8 s) | 14.552 sec (0 m 14 s) | 8.224 sec (0 m 8 s) |
| Infected | 0 | 0 | 0 |
| Install source | Cisco Talos RPM | EPEL | Cisco Talos RPM |
| `--json` support | No | No | No |

**Why AL2 stays on 1.4.3:** The Cisco Talos RPM requires glibc 2.28, but Amazon Linux 2 ships glibc 2.26. The EPEL package is the only option for AL2.

---

## Section 2: AIDE Results

### How AIDE Tests Work

AIDE is a **stateful** file integrity monitor. It works in three phases:

1. **`aide --init`** — Scans the filesystem and builds a baseline database (`aide.db.gz`)
2. **`aide --check`** (or `-C`) — Compares the current filesystem against the baseline
3. **`aide --update`** — Refreshes the baseline after confirmed changes

In our Docker images, `--init` runs at **build time**. The baseline is baked into the image. When `docker run` creates a new container, the filesystem differs from the build-time baseline in predictable ways (Docker injects its own `/etc/hosts`, `/etc/resolv.conf`, `/etc/hostname`).

Each image runs two checks:

1. **Clean check** — `aide -C 2>&1 | aide-to-json.py` against the unmodified container
2. **Tampered check** — After writing `/tmp/ci-test-hack` and `chmod 777 /etc/resolv.conf`, then `aide -C 2>&1 | aide-to-json.py`

Both are piped through `aide-to-json.py` which produces one JSON line per check and appends to `/var/log/aide/aide.jsonl`.

### Important: Why "Clean" Checks Show Changes

You'll notice that even the "clean" checks report `changes_detected` rather than `clean`. This is **expected Docker behavior**, not a bug. Here's why:

When Docker creates a container from an image, it modifies several files that AIDE baselined at build time:

| File | Why it changes |
|------|----------------|
| `/etc/hostname` | Docker assigns a random container ID as hostname |
| `/etc/hosts` | Docker injects hostname-to-IP mappings for the container |
| `/etc/resolv.conf` | Docker configures DNS to point to its internal DNS server |
| `/var/log/aide` | The `mkdir -p /var/log/aide` in the test script creates this directory |

On a **production host** (not Docker), after running `aide --init` and then `aide --check` without modifying any files, you'd get `"result": "clean"` with zero changes.
### AIDE — AlmaLinux 9

**File:** `aide/almalinux9/aide.log`

| Field | Clean Check | Tampered Check |
|-------|-------------|----------------|
| AIDE Version | 0.16 | 0.16 |
| Total entries | 9404 | 9404 |
| Added | 0 | 0 |
| Removed | 0 | 0 |
| Changed | 12 | 12 |
| Run time | 0m 3s | N/A |
| Permission tamper detected | — | Yes |

**Notes:** AIDE 0.16 on AlmaLinux 9 uses SHA512 as its default hash algorithm. Python `__pycache__` directories appear as linkcount changes because running the parser creates them.

**Database hash algorithms:** 2,4Y,MD5,RMD160,SHA1,SHA256,SHA512,TIGER,X

**File:** `aide/almalinux9/aide.json` — 2 JSON lines

### AIDE — Amazon Linux 2

**File:** `aide/amazonlinux2/aide.log`

| Field | Clean Check | Tampered Check |
|-------|-------------|----------------|
| AIDE Version | 0.16.2 | 0.16.2 |
| Total entries | 22470 | 22470 |
| Added | 1 | 1 |
| Removed | 0 | 0 |
| Changed | 3 | 3 |
| Run time | 0m 6s | 0m 3s |
| Permission tamper detected | — | Yes |

**Notes:** AIDE 0.16.2 reports **22470 total entries** — more than AL9 because the default `aide.conf` monitors broader directory trees. Uses SHA256 as its default hash.

**Database hash algorithms:** AF,MD5,RMD160,SHA1,SHA256,SHA512,TIGER,W0J

**File:** `aide/amazonlinux2/aide.json` — 2 JSON lines

### AIDE — Amazon Linux 2023

**File:** `aide/amazonlinux2023/aide.log`

| Field | Clean Check | Tampered Check |
|-------|-------------|----------------|
| AIDE Version | 0.18.6 | 0.18.6 |
| Total entries | 8299 | 8299 |
| Added | 1 | 1 |
| Removed | 0 | 0 |
| Changed | 59 | 59 |
| Run time | 0m 4s | N/A |
| Permission tamper detected | — | Yes |

**Notes:** AIDE 0.18.6 reports **59 changed entries** — far more than AL9 or AL2. This is because 0.18.6 tracks **Inode** and **Ctime** by default, and Docker's layer copy shifts every inode/ctime. On a production host (not Docker), these would not appear.

**Database hash algorithms:** 6,8K,8V,CRC32,GOST,MD5,OTCM,RMD160,SHA1,SHA256,SHA512,STRIBOG256,STRIBOG512,TIGER,WHIRLPOOL

**File:** `aide/amazonlinux2023/aide.json` — 2 JSON lines

### AIDE Cross-OS Comparison

| Metric | AL9 (0.16) | AL2 (0.16.2) | AL2023 (0.18.6) |
|--------|------------|--------------|------------------|
| Total entries | 9404 | 22470 | 8299 |
| Changed (clean) | 12 | 3 | 59 |
| Added (clean) | 0 | 1 | 1 |
| Run time | 0m 3s | 0m 6s | 0m 4s |
| Inode tracking | No (not in config) | No | Yes (default in 0.18.x) |
| Native JSON | No | No | Yes (`report_format=json`) |

**Hash algorithms by OS:**

| Algorithm | AL9 (0.16) | AL2 (0.16.2) | AL2023 (0.18.6) |
|-----------|:----------:|:------------:|:----------------:|
| MD5 | Yes | Yes | Yes |
| SHA1 | Yes | Yes | Yes |
| RMD160 | Yes | Yes | Yes |
| TIGER | Yes | Yes | Yes |
| SHA256 | Yes | Yes | Yes |
| SHA512 | Yes | Yes | Yes |
| CRC32 |   |   | Yes |
| WHIRLPOOL |   |   | Yes |
| GOST |   |   | Yes |
| STRIBOG256 |   |   | Yes |
| STRIBOG512 |   |   | Yes |

---

## Section 3: JSONL Append Validation

Every test produced a JSONL file with exactly 2 lines (one per scan/check). This validates the core SIEM ingestion pipeline:

**ClamAV** — `clamscan.jsonl`:
```
Line 1: WITH summary scan    → {"file_results":[...],"scan_summary":{...},"hostname":"...","timestamp":"..."}
Line 2: WITHOUT summary scan → {"file_results":[...],"hostname":"...","timestamp":"..."}
```

**AIDE** — `aide.jsonl`:
```
Line 1: Clean check    → {"result":"changes_detected","summary":{...},"changed_entries":[...],"scanner":"aide"}
Line 2: Tampered check → {"result":"changes_detected","summary":{...},"changed_entries":[...],"scanner":"aide"}
```

**What this proves:**
- Each scan/check produces exactly one JSON line (no multi-line pretty-printing)
- Lines are appended (not overwritten), so the file grows with each scan
- Each line is independently parseable by SIEM tools (Filebeat, Fluentd, rsyslog)
- The `timestamp` field is unique per line, enabling time-series queries

**SIEM query examples** (after deploying to production hosts):
```bash
# Last ClamAV scan result
tail -1 /var/log/clamav/clamscan.jsonl | jq .

# All AIDE checks that found changes
jq 'select(.result == "changes_detected")' /var/log/aide/aide.jsonl

# Files with permission changes (security alert)
jq '.detailed_changes[] | select(.attribute == "Perm")' /var/log/aide/aide.jsonl
```
---

## Section 4: File Inventory

All test output files are in the per-OS `results/` directories:

```
linux-security-scanners/
├── TEST-RESULTS-BREAKDOWN.md          ← This file (auto-generated)
├── clamav/
│   ├── almalinux9/
│   │   └── results/
│   │       ├── clamscan.log    (907 B)
│   │       └── clamscan.json   (848 B)
│   ├── amazonlinux2/
│   │   └── results/
│   │       ├── clamscan.log    (898 B)
│   │       └── clamscan.json   (848 B)
│   ├── amazonlinux2023/
│   │   └── results/
│   │       ├── clamscan.log    (909 B)
│   │       └── clamscan.json   (845 B)
├── aide/
│   ├── almalinux9/
│   │   └── results/
│   │       ├── aide.log    (7 KB)
│   │       └── aide.json   (3 KB)
│   ├── amazonlinux2/
│   │   └── results/
│   │       ├── aide.log    (4 KB)
│   │       └── aide.json   (2 KB)
│   ├── amazonlinux2023/
│   │   └── results/
│   │       ├── aide.log    (27 KB)
│   │       └── aide.json   (10 KB)
```

**File sizes:**

| File | Size |
|------|------|
| `clamav/almalinux9/results/clamscan.log` | 907 B |
| `clamav/almalinux9/results/clamscan.json` | 848 B |
| `clamav/amazonlinux2/results/clamscan.log` | 898 B |
| `clamav/amazonlinux2/results/clamscan.json` | 848 B |
| `clamav/amazonlinux2023/results/clamscan.log` | 909 B |
| `clamav/amazonlinux2023/results/clamscan.json` | 845 B |
| `aide/almalinux9/results/aide.log` | 7 KB |
| `aide/almalinux9/results/aide.json` | 3 KB |
| `aide/amazonlinux2/results/aide.log` | 4 KB |
| `aide/amazonlinux2/results/aide.json` | 2 KB |
| `aide/amazonlinux2023/results/aide.log` | 27 KB |
| `aide/amazonlinux2023/results/aide.json` | 10 KB |

---

_Generated by `scripts/generate-report.sh` on 2026-04-24_
