# CLAUDE.md

## Project Overview

Linux Security Scanners is a collection of Docker-based testing environments and production deployment tooling for Linux file integrity and antivirus scanners. Each scanner subdirectory contains pre-built Docker images, JSON output parsers, systemd unit files, and SIEM ingestion guides.

Currently supported scanners:
- **ClamAV** — Antivirus scanner
- **AIDE** — Advanced Intrusion Detection Environment (file integrity)

Supported operating systems:
- AlmaLinux 9 (RHEL 9 compatible)
- Amazon Linux 2
- Amazon Linux 2023

## Project Structure

```
linux-security-scanners/
├── CLAUDE.md                  # This file
├── .zread/                    # AI-generated project wiki (zread CLI)
│   └── wiki/                  # Run `zread generate` to update
│       ├── current            # Pointer to latest version
│       └── versions/          # Dated snapshots of wiki pages
├── scripts/
│   ├── run-tests.sh           # Build + test runner (populates results/ + generates report)
│   ├── generate-report.sh     # Generates TEST-RESULTS-BREAKDOWN.md from results
│   ├── validate-clamav-jsonl.py # CI JSONL validation
│   └── validate-aide-jsonl.py   # CI JSONL validation
├── clamav/                    # ClamAV scanner tooling
│   ├── README.md              # Full ClamAV guide
│   ├── shared/                # Cross-platform scripts & systemd files
│   ├── almalinux9/
│   │   ├── Dockerfile         # AlmaLinux 9 + ClamAV 1.5.2 (Cisco Talos RPM)
│   │   └── results/           # Sample test outputs (clamscan.log, clamscan.json)
│   ├── amazonlinux2/
│   │   ├── Dockerfile         # Amazon Linux 2 + ClamAV 1.4.3 (EPEL)
│   │   └── results/           # Sample test outputs
│   └── amazonlinux2023/
│       ├── Dockerfile         # Amazon Linux 2023 + ClamAV 1.5.2 (Cisco Talos RPM)
│       └── results/           # Sample test outputs
└── aide/                      # AIDE file integrity scanner tooling
    ├── README.md              # Full AIDE guide
    ├── shared/                # Cross-platform scripts & systemd files
    ├── almalinux9/
    │   ├── Dockerfile         # AlmaLinux 9 + AIDE 0.16
    │   └── results/           # Sample test outputs (aide.log, aide.json)
    ├── amazonlinux2/
    │   ├── Dockerfile         # Amazon Linux 2 + AIDE 0.16.2
    │   └── results/           # Sample test outputs
    └── amazonlinux2023/
        ├── Dockerfile         # Amazon Linux 2023 + AIDE 0.18.6
        ├── results/           # Sample test outputs (aide.log, aide.json)
        ├── native-json-comparison.md  # Native JSON vs wrapper analysis
        └── native-json-demo.sh        # report_format=json reproducer
```

## Common Patterns

### Docker Images

Each scanner/OS combo has a pre-built Docker image with the scanner + Python baked in:
```bash
# Build from project root
docker build -t almalinux9-clamav:latest -f clamav/almalinux9/Dockerfile .
docker build -t almalinux9-aide:latest -f aide/almalinux9/Dockerfile .
```

### JSON Output Pipeline

All scanners follow the same pattern:
```
scanner_command | /usr/local/bin/scanner-to-json.py
```

The Python parser:
1. Reads scanner text output from stdin
2. Parses into structured JSON
3. Prints one-line JSON to stdout (captured by systemd journal)
4. Appends to `/var/log/<scanner>/<scanner>.jsonl` (JSONL format for SIEM tailing)

### SIEM Ingestion

Each scanner's JSONL file is designed for log shipper tailing (Filebeat, Fluentd, rsyslog). Logrotate configs handle rotation (30-day retention).

### Systemd Timers

Each scanner has a systemd timer that runs daily at a randomized time to avoid thundering herd across hosts.

### AIDE JSON Output Fields

The `aide-to-json.py` parser captures these fields from AIDE text output:

| Field | Type | When Present |
|-------|------|-------------|
| `result` | string | Always — `"clean"` or `"changes_detected"` |
| `outline` | string | Always — AIDE's status message |
| `summary` | object | When changes detected — `total_entries`, `added`, `removed`, `changed` counts |
| `added_entries` | array | When files added — `{"path": "...", "flags": "f++++++++++++++++"}` |
| `removed_entries` | array | When files removed — `{"path": "...", "flags": "f----------------"}` |
| `changed_entries` | array | When files changed — `{"path": "...", "flags": "f > p..    .CA."}` |
| `detailed_changes` | array | When files changed — `{"path", "attribute", "old", "new"}` per attribute |
| `databases` | object | Always — integrity hashes of AIDE DB, keyed by path then algorithm |
| `run_time_seconds` | integer | Always — scan duration |
| `hostname` | string | Always — added by parser |
| `timestamp` | string | Always — ISO 8601 UTC, added by parser |
| `scanner` | string | Always — `"aide"`, added by parser |

Empty collections and unset fields are omitted from output.

## Key Findings Across Scanners

| Scanner | Native JSON Support? | Workaround |
|---------|---------------------|------------|
| ClamAV 1.5.2 (AL9, AL2023) / 1.4.3 (AL2) | No (`--json` not compiled) | Python parser |
| AIDE 0.16 (AL9, AL2) | No (`report_format` option doesn't exist in 0.16.x) | Python parser |
| AIDE 0.18.6 (AL2023) | Yes — `report_format=json` works, but is order-sensitive in `aide.conf` (must precede `report_url=` lines, or be set via `-B` on the CLI) | Python parser (for uniform schema across all three OSes + JSONL output) |

## Build and Development Commands

```bash
# Build all images from project root
docker build -t almalinux9-clamav:latest -f clamav/almalinux9/Dockerfile .
docker build -t amazonlinux2-clamav:latest -f clamav/amazonlinux2/Dockerfile .
docker build -t amazonlinux2023-clamav:latest -f clamav/amazonlinux2023/Dockerfile .
docker build -t almalinux9-aide:latest -f aide/almalinux9/Dockerfile .
docker build -t amazonlinux2-aide:latest -f aide/amazonlinux2/Dockerfile .
docker build -t amazonlinux2023-aide:latest -f aide/amazonlinux2023/Dockerfile .

# Or use the test runner to build + generate results:
./scripts/run-tests.sh              # Build all + run all tests + generate report
./scripts/run-tests.sh --build-only # Build only, skip tests
./scripts/run-tests.sh --scanner clamav --os almalinux9  # Single combo

# Generate report from existing results (no Docker needed):
./scripts/generate-report.sh                    # Default: TEST-RESULTS-BREAKDOWN.md
./scripts/generate-report.sh --output other.md  # Custom output path

# Quick test any image
docker run --rm <image_tag> <scanner_command> --version

# Full scan test
docker run --rm <image_tag> bash -c '
  mkdir -p /var/log/<scanner>
  <scanner_command> | python3 /usr/local/bin/<scanner>-to-json.py
'
```

## Cross-Platform Notes

- All testing done on Windows 11 Docker Desktop
- Dockerfiles use `COPY <scanner>/shared/` from project root context (e.g. `COPY clamav/shared/clamscan-to-json.py`)
- Python scripts use only stdlib (no pip dependencies)
- Shell commands use Unix syntax (Git Bash compatible)
- `.gitattributes` enforces LF line endings on `*.sh` files so they run inside Linux containers from any host OS

## Zread Wiki (`.zread/`)

The `.zread/` directory holds an AI-generated project wiki created by the [Zread CLI](https://zread.ai/cli). It provides a browsable, structured breakdown of the codebase across 20+ topics.

### Maintenance workflow

```bash
zread generate              # Generate or update the wiki
zread browse                # Open in browser
```

- **Before committing updates:** prune old dated snapshots so the repo only contains the latest version:
  ```bash
  # Keep only the latest version, remove older snapshots
  cd .zread/wiki/versions/
  ls -1t | tail -n +2 | xargs rm -rf
  cd -
  ```
- Git history tracks what changed between updates — no need to keep multiple dated snapshots in the working tree.
- `.zread/wiki/drafts/` is gitignored (in-progress generation artifacts).

## CI

GitHub Actions workflow at `.github/workflows/ci.yml` runs on push/PR to `master`. Builds all 6 Docker images (2 scanners x 3 OSes) in parallel and runs scan-to-JSON smoke tests with JSONL validation. Uses `actions/checkout@v5`. Validation scripts are in `scripts/`.
