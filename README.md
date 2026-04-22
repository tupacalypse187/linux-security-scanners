# 🛡️ Linux Security Scanners

> Docker-based testing environments and production deployment tooling for Linux security scanners.
> Outputs structured JSON for SIEM ingestion across AlmaLinux 9, Amazon Linux 2, and Amazon Linux 2023.

---

## 📦 Scanners

| Scanner | Description | Versions |
|---------|-------------|----------|
| [🔒 ClamAV](clamav/README.md) | Antivirus scanner | 1.4.3 (AL9, AL2) · 1.5.2 (AL2023) |
| [🔐 AIDE](aide/README.md) | File integrity monitoring | 0.16 (AL9) · 0.16.2 (AL2) · 0.18.6 (AL2023) |

---

## 📁 Project Structure

```
linux-security-scanners/
├── CLAUDE.md              # Project instructions for Claude Code
├── README.md              # This file
├── .gitignore
├── clamav/                # ClamAV scanner tooling
│   ├── README.md          # Full guide: Docker images, JSON parser, systemd, SIEM, jq
│   ├── shared/            # Cross-platform scripts & systemd units
│   ├── almalinux9/        # AlmaLinux 9 + ClamAV 1.4.3 (EPEL)
│   ├── amazonlinux2/      # Amazon Linux 2 + ClamAV 1.4.3 (EPEL)
│   └── amazonlinux2023/   # Amazon Linux 2023 + ClamAV 1.5.2 (Cisco Talos RPM)
└── aide/                  # AIDE file integrity scanner tooling
    ├── README.md          # Full guide: Docker images, JSON parser, systemd, SIEM, jq
    ├── shared/            # Cross-platform scripts & systemd units
    ├── almalinux9/        # AlmaLinux 9 + AIDE 0.16
    ├── amazonlinux2/      # Amazon Linux 2 + AIDE 0.16.2
    └── amazonlinux2023/   # Amazon Linux 2023 + AIDE 0.18.6
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
| `README.md` | Full documentation with jq examples |

---

## 🔍 Key Findings

### None of the tested builds have native JSON output

| Scanner | OS | Native JSON? | Workaround |
|---------|-----|-------------|------------|
| ClamAV 1.4.3 | AL9, AL2 | `--json` not compiled in | Python parser |
| ClamAV 1.5.2 | AL2023 | `--json` not in Cisco RPM | Python parser |
| AIDE 0.16/0.16.2 | AL9, AL2 | No JSON support | Python parser |
| AIDE 0.18.6 | AL2023 | `report_format=json` accepted but non-functional | Python parser |

### Amazon Linux 2023 ClamAV gotchas

The Cisco Talos RPM installs to `/usr/local/` prefix and requires:
- `--allowerasing` to resolve `libcurl` / `libcurl-minimal` conflict
- `shadow-utils` for `useradd`
- Manual `freshclam.conf` creation at `/usr/local/etc/`

---

## 📖 Detailed Documentation

- [ClamAV README](clamav/README.md) — Full guide with OS matrix, Dockerfiles, systemd units, SIEM integration, and jq commands
- [AIDE README](aide/README.md) — Full guide with OS matrix, Dockerfiles, systemd units, SIEM integration, and jq commands
- [CLAUDE.md](CLAUDE.md) — Project instructions for Claude Code

---

## 🧹 Cleanup All Docker Images

```bash
docker rmi \
  almalinux9-clamav:latest amazonlinux2-clamav:latest amazonlinux2023-clamav:latest \
  almalinux9-aide:latest amazonlinux2-aide:latest amazonlinux2023-aide:latest
docker image prune -f
```
