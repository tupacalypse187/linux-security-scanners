# 🛡️ Linux Security Scanners

> Docker-based testing environments and production deployment tooling for Linux security scanners.
> Outputs structured JSON for SIEM ingestion across AlmaLinux 9, Amazon Linux 2, and Amazon Linux 2023.

---

## 📦 Scanners

| Scanner | Description | Versions |
|---------|-------------|----------|
| [🔒 ClamAV](clamav/README.md) | Antivirus scanner | 1.5.2 (AL9, AL2023, Cisco Talos RPM) · 1.4.3 (AL2, EPEL) |
| [🔐 AIDE](aide/README.md) | File integrity monitoring | 0.16 (AL9) · 0.16.2 (AL2) · 0.18.6 (AL2023) |

---

## 📁 Project Structure

```
linux-security-scanners/
├── CLAUDE.md              # Project instructions for Claude Code
├── TEST-RESULTS-BREAKDOWN.md  # Auto-generated test results report
├── scripts/
│   ├── run-tests.sh       # Build + test runner (populates results/ + generates report)
│   ├── generate-report.sh # Generates TEST-RESULTS-BREAKDOWN.md from results
│   ├── validate-clamav-jsonl.py  # CI JSONL validation
│   └── validate-aide-jsonl.py    # CI JSONL validation
├── clamav/                # ClamAV scanner tooling
│   ├── README.md          # Full guide: Docker images, JSON parser, systemd, SIEM, jq
│   ├── shared/            # Cross-platform scripts & systemd units
│   ├── almalinux9/        # AlmaLinux 9 + ClamAV 1.5.2 (Cisco Talos RPM)
│   │   └── results/       # Sample outputs: clamscan.log, clamscan.json
│   ├── amazonlinux2/      # Amazon Linux 2 + ClamAV 1.4.3 (EPEL)
│   │   └── results/       # Sample outputs
│   └── amazonlinux2023/   # Amazon Linux 2023 + ClamAV 1.5.2 (Cisco Talos RPM)
│       └── results/       # Sample outputs
└── aide/                  # AIDE file integrity scanner tooling
    ├── README.md          # Full guide: Docker images, JSON parser, systemd, SIEM, jq
    ├── shared/            # Cross-platform scripts & systemd units
    ├── almalinux9/        # AlmaLinux 9 + AIDE 0.16
    │   └── results/       # Sample outputs: aide.log, aide.json
    ├── amazonlinux2/      # Amazon Linux 2 + AIDE 0.16.2
    │   └── results/       # Sample outputs
    └── amazonlinux2023/   # Amazon Linux 2023 + AIDE 0.18.6
        ├── results/       # Sample outputs
        ├── native-json-comparison.md  # Native JSON vs wrapper analysis
        └── native-json-demo.sh        # report_format=json reproducer
```

---

## 🐧 Supported Operating Systems

| OS | Docker Tag Pattern | Package Manager |
|----|-------------------|-----------------|
| AlmaLinux 9 (RHEL 9) | `almalinux9-*` | `dnf` |
| Amazon Linux 2 | `amazonlinux2-*` | `yum` |
| Amazon Linux 2023 | `amazonlinux2023-*` | `dnf` |

---

## 🚀 Quick Start

### Build All Images

```bash
# From project root
# ClamAV
docker build -t almalinux9-clamav:latest -f clamav/almalinux9/Dockerfile .
docker build -t amazonlinux2-clamav:latest -f clamav/amazonlinux2/Dockerfile .
docker build -t amazonlinux2023-clamav:latest -f clamav/amazonlinux2023/Dockerfile .

# AIDE
docker build -t almalinux9-aide:latest -f aide/almalinux9/Dockerfile .
docker build -t amazonlinux2-aide:latest -f aide/amazonlinux2/Dockerfile .
docker build -t amazonlinux2023-aide:latest -f aide/amazonlinux2023/Dockerfile .
```

### Or Use the Test Runner

```bash
# Build all images + run scans + save results to */results/ directories
./scripts/run-tests.sh

# Build only (no scans)
./scripts/run-tests.sh --build-only

# Single scanner/OS combo
./scripts/run-tests.sh --scanner aide --os amazonlinux2023
```

### Run a Quick Test

```bash
# ClamAV scan with JSON output
docker run --rm almalinux9-clamav:latest bash -c '
  mkdir -p /var/log/clamav
  clamscan /etc/hostname /etc/hosts | python3 /usr/local/bin/clamscan-to-json.py
'

# AIDE check with JSON output
docker run --rm almalinux9-aide:latest bash -c '
  mkdir -p /var/log/aide
  aide -C 2>&1 | python3 /usr/local/bin/aide-to-json.py
'
```

---

## ⚙️ Common Architecture

Both scanners follow the same pipeline pattern:

```
scanner_command
       │
       ▼  (pipe)
*-to-json.py
       │
       ├──▶ stdout → systemd journal
       └──▶ /var/log/<scanner>/<scanner>.jsonl (append)
                 │
                 ▼
       Filebeat / Fluentd / rsyslog → SIEM
```

### What's in each scanner directory

| File | Purpose |
|------|---------|
| `*/Dockerfile` | Pre-built image with scanner + Python + parser baked in |
| `shared/*-to-json.py` | Text-to-JSON parser (one line per scan/check) |
| `shared/*-scan.service` | Systemd service (runs scanner, pipes to parser) |
| `shared/*-scan.timer` | Systemd timer (daily, randomized delay) |
| `shared/*-jsonl.conf` | Logrotate config (30-day retention) |
| `*/results/` | Sample test outputs showing raw scanner output + JSON conversion |
| `README.md` | Full documentation with jq examples |

### Sample Results

Each scanner/OS directory contains a `results/` folder with sample test outputs you can use as reference:

| File | Contents |
|------|----------|
| `clamav/*/results/clamscan.log` | Raw clamscan output: with summary vs without `--no-summary` |
| `clamav/*/results/clamscan.json` | JSON parser output: compact line + pretty-printed |
| `aide/*/results/aide.log` | Raw AIDE output: clean check + tampered file check |
| `aide/*/results/aide.json` | JSON parser output: compact line + pretty-printed |

To regenerate these results on your machine:

```bash
./scripts/run-tests.sh   # Builds images + saves results to */results/ + generates TEST-RESULTS-BREAKDOWN.md
```

### Test Results Report

Running `./scripts/run-tests.sh` (or `./scripts/generate-report.sh` standalone) produces `TEST-RESULTS-BREAKDOWN.md` — a detailed breakdown of all test results across scanners and OSes, including version numbers, scan timings, entry counts, changed file lists, cross-OS comparison tables, and a full file inventory. No LLM needed — it's pure bash/sed/jq.

---

## 🔍 Key Findings

### Native JSON support is uneven — the Python parser normalises it

| Scanner | OS | Native JSON? | Notes |
|---------|-----|-------------|-------|
| ClamAV 1.5.2 | AL9, AL2023 | ❌ `--json` not compiled into the Cisco RPM | Python parser |
| ClamAV 1.4.3 | AL2 | ❌ `--json` not compiled into the EPEL build | Python parser |
| AIDE 0.16 / 0.16.2 | AL9, AL2 | ❌ `report_format` option unknown in 0.16.x | Python parser |
| AIDE 0.18.6 | AL2023 | ✅ Works via `report_format=json` — but order-sensitive in `aide.conf` (see [AIDE README](aide/README.md#about-report_formatjson-on-amazon-linux-2023)) | Python parser for uniform schema + JSONL |

The Python parser is still the recommended path on AL2023 because it produces the same SIEM-ready JSONL schema across all three OSes and enriches each record with `hostname`, `timestamp`, and `scanner` fields that the native AIDE JSON does not emit. See [native JSON vs wrapper comparison](aide/amazonlinux2023/native-json-comparison.md) for a detailed side-by-side analysis.

### Cisco Talos RPM gotchas (AL9, AL2023)

The Cisco Talos RPM installs to `/usr/local/` prefix and requires:
- `--allowerasing` to resolve `libcurl` / `libcurl-minimal` conflict (AL9, AL2023)
- `shadow-utils` for `useradd`
- Manual `freshclam.conf` creation at `/usr/local/etc/`

> **Amazon Linux 2** uses EPEL ClamAV 1.4.3 (the Cisco RPM requires glibc 2.28, but AL2 ships glibc 2.26).

---

## 📖 Detailed Documentation

- [ClamAV README](clamav/README.md) — Full guide with OS matrix, Dockerfiles, systemd units, SIEM integration, and jq commands
- [AIDE README](aide/README.md) — Full guide with OS matrix, Dockerfiles, systemd units, SIEM integration, and jq commands
- [CLAUDE.md](CLAUDE.md) — Project instructions for Claude Code
- [`.zread/wiki/`](.zread/wiki/) — AI-generated project wiki ([Zread CLI](https://zread.ai/cli))

---

## 🧹 Cleanup All Docker Images

```bash
docker rmi \
  almalinux9-clamav:latest amazonlinux2-clamav:latest amazonlinux2023-clamav:latest \
  almalinux9-aide:latest amazonlinux2-aide:latest amazonlinux2023-aide:latest
docker image prune -f
```

---

## ✅ CI / GitHub Actions

Automated workflow (`.github/workflows/ci.yml`) runs on every push and PR to `master`.

**What it tests (6 parallel jobs — 2 scanners x 3 OSes):**

| Step | What it verifies |
|------|-----------------|
| Build image | Dockerfile builds without errors; base image and packages resolve |
| Verify version | Scanner binary is installed and functional |
| Smoke test — JSON output | Scan produces valid JSON through the text-to-JSON pipeline |
| Smoke test — JSONL append + validation | Two sequential scans append to JSONL file; validation script confirms correct line count and required fields |
| Generate sample results | Runs scans and saves `*.log` + `*.json` output as downloadable artifacts |

**Artifacts:** Each CI run uploads sample results as downloadable artifacts (30-day retention). Look for `clamav-<os>-results` and `aide-<os>-results` on any workflow run.

**Status:** Runs clean with no warnings. Uses `actions/checkout@v5` (Node 24).

---

## 🔮 Future Enhancements

- **OpenSCAP scanner** — Add compliance scanning (CIS benchmarks) as a third scanner alongside ClamAV and AIDE, completing the host security triad (antivirus + file integrity + compliance).
- **Alerting wrapper** — A small post-scan script that parses JSONL output and sends Slack/email/webhook alerts when ClamAV finds infected files or AIDE detects file changes. Provides push notifications beyond passive jq queries.
