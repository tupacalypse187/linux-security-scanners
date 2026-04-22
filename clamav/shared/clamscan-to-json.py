#!/usr/bin/env python3
"""
Converts clamscan output to single-line JSON for SIEM ingestion.

Usage:
    clamscan /path/to/scan | clamscan-to-json.py
    clamscan /path/to/scan > /tmp/scan.txt && cat /tmp/scan.txt | clamscan-to-json.py

Designed to be piped from the systemd service. Outputs one JSON object per scan.
Appends to /var/log/clamav/clamscan.jsonl (JSONL format - one JSON object per line).
"""

import json, re, sys, socket
from datetime import datetime, timezone


def parse_clamscan(raw: str) -> dict:
    result = {"file_results": [], "scan_summary": {}}
    in_summary = False

    for line in raw.splitlines():
        line = line.strip()

        if "--- SCAN SUMMARY ---" in line:
            in_summary = True
            continue

        if not in_summary:
            m = re.match(r"^(.+?):\s+(OK|FOUND.*)$", line)
            if m:
                result["file_results"].append({
                    "file": m.group(1).strip(),
                    "status": m.group(2).strip(),
                })
        else:
            m2 = re.match(r"^([\w\s]+?):\s+(.+)$", line)
            if m2:
                key = m2.group(1).strip().lower().replace(" ", "_")
                val = m2.group(2).strip()
                # Convert numeric strings
                if key in ("known_viruses", "scanned_directories", "scanned_files", "infected_files"):
                    try:
                        val = int(val)
                    except ValueError:
                        pass
                result["scan_summary"][key] = val

    if not result["scan_summary"]:
        del result["scan_summary"]

    return result


def main():
    raw = sys.stdin.read()
    if not raw.strip():
        sys.exit(0)

    parsed = parse_clamscan(raw)

    parsed["hostname"] = socket.gethostname()
    parsed["timestamp"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    json_line = json.dumps(parsed, separators=(",", ":"))

    # Output to stdout (captured by journalctl)
    print(json_line)

    # Append to JSONL log file for SIEM shipper to tail
    log_file = "/var/log/clamav/clamscan.jsonl"
    try:
        with open(log_file, "a") as f:
            f.write(json_line + "\n")
    except PermissionError:
        # Fallback: just stdout, let systemd journal capture it
        pass


if __name__ == "__main__":
    main()
