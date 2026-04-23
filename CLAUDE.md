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
├── scripts/
│   ├── run-tests.sh           # Build + test runner (populates results/)
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
./scripts/run-tests.sh              # Build all + run all tests
./scripts/run-tests.sh --build-only # Build only, skip tests
./scripts/run-tests.sh --scanner clamav --os almalinux9  # Single combo

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

## CI

GitHub Actions workflow at `.github/workflows/ci.yml` runs on push/PR to `master`. Builds all 6 Docker images (2 scanners x 3 OSes) in parallel and runs scan-to-JSON smoke tests with JSONL validation. Uses `actions/checkout@v5`. Validation scripts are in `scripts/`.
