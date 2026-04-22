#!/usr/bin/env python3
"""
Converts AIDE check output to single-line JSON for SIEM ingestion.
Mimics the report_format=json schema from AIDE v0.18 documentation.

Usage:
    aide -C | aide-to-json.py
    aide -C -c /etc/aide.conf 2>&1 | aide-to-json.py

Outputs one JSON object per check. Appends to /var/log/aide/aide.jsonl.
"""

import json, re, sys, socket
from datetime import datetime, timezone


def parse_aide(raw: str) -> dict:
    result = {
        "result": "clean",
        "summary": {},
        "added_entries": [],
        "removed_entries": [],
        "changed_entries": [],
        "detailed_changes": [],
    }

    section = None
    current_file = None

    for line in raw.splitlines():
        s = line.strip()

        # Detect outcome
        if "NO differences" in s:
            result["result"] = "clean"
        elif "found differences" in s:
            result["result"] = "changes_detected"

        # Summary lines: "Total number of entries:\t12345"
        m = re.match(r"^(Total number of entries|Added entries|Removed entries|Changed entries)\s*:\s*(\d+)$", s)
        if m:
            key_map = {
                "Total number of entries": "total_entries",
                "Added entries": "added",
                "Removed entries": "removed",
                "Changed entries": "changed",
            }
            result["summary"][key_map[m.group(1)]] = int(m.group(2))
            continue

        # Section headers
        if s.startswith("Added entries"):
            section = "added"
            continue
        elif s.startswith("Removed entries"):
            section = "removed"
            continue
        elif s.startswith("Changed entries"):
            section = "changed"
            continue
        elif s.startswith("Detailed information"):
            section = "detail"
            continue

        # Skip separators
        if s.startswith("---"):
            continue

        # Parse entry lines: "f++++++++++++++++: /path"  or "f----------------: /path" or "f = ...H...: /path"
        if section in ("added", "removed", "changed"):
            m = re.match(r"^[fdlbcps]\s+(\S+)\s*:\s+(.+)$", s)
            if m:
                attrs = m.group(1)
                path = m.group(2).strip()
                entry = {"path": path, "attributes": attrs}
                if section == "added":
                    result["added_entries"].append(entry)
                elif section == "removed":
                    result["removed_entries"].append(entry)
                elif section == "changed":
                    entry["changed_attrs"] = attrs
                    result["changed_entries"].append(entry)
            continue

        # Detailed change lines
        if section == "detail":
            # File: /path
            m = re.match(r"^File:\s+(.+)$", s)
            if m:
                current_file = m.group(1).strip()
                continue
            # SHA256    : oldhash | newhash
            m = re.match(r"^(\w+)\s*:\s+(.+)$", s)
            if m and current_file and "|" in m.group(2):
                attr = m.group(1).strip()
                vals = m.group(2).split("|")
                if len(vals) >= 2:
                    change = {
                        "path": current_file,
                        "attribute": attr,
                        "old": vals[0].strip(),
                        "new": vals[1].strip(),
                    }
                    result["detailed_changes"].append(change)
                continue

    # Clean up empty arrays
    for key in ("added_entries", "removed_entries", "changed_entries", "detailed_changes"):
        if not result[key]:
            del result[key]

    if not result["summary"]:
        del result["summary"]

    return result


def main():
    raw = sys.stdin.read()
    if not raw.strip():
        sys.exit(0)

    parsed = parse_aide(raw)

    parsed["hostname"] = socket.gethostname()
    parsed["timestamp"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    parsed["scanner"] = "aide"

    json_line = json.dumps(parsed, separators=(",", ":"))

    print(json_line)

    log_file = "/var/log/aide/aide.jsonl"
    try:
        with open(log_file, "a") as f:
            f.write(json_line + "\n")
    except PermissionError:
        pass


if __name__ == "__main__":
    main()
