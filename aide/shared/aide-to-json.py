#!/usr/bin/env python3
"""
Converts AIDE check output to single-line JSON for SIEM ingestion.

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
        "outline": None,
        "summary": {},
        "added_entries": [],
        "removed_entries": [],
        "changed_entries": [],
        "detailed_changes": [],
        "databases": {},
        "run_time_seconds": None,
    }

    section = None
    current_file = None
    current_db = None
    current_hash_name = None

    for line in raw.splitlines():
        s = line.strip()
        if not s:
            continue

        # Detect outcome + outline message
        if "NO differences" in s:
            result["result"] = "clean"
            result["outline"] = s
        elif "found differences" in s:
            result["result"] = "changes_detected"
            result["outline"] = s

        # Run time: "End timestamp: ... (run time: 0m 4s)"
        m = re.match(r"^End timestamp:.*run time:\s*(\d+)m\s*(\d+)s\)", s)
        if m:
            result["run_time_seconds"] = int(m.group(1)) * 60 + int(m.group(2))
            continue

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
            current_db = None
            continue
        elif s.startswith("Removed entries"):
            section = "removed"
            current_db = None
            continue
        elif s.startswith("Changed entries"):
            section = "changed"
            current_db = None
            continue
        elif s.startswith("Detailed information"):
            section = "detail"
            current_db = None
            continue
        elif "attributes of the (uncompressed) database" in s:
            section = "databases"
            current_db = None
            current_hash_name = None
            continue

        # Skip separators
        if s.startswith("---"):
            continue

        # Parse entry lines (added/removed/changed)
        # Format: "f++++++++++++++++: /path" or "f > ... mc..H..  : /path"
        if section in ("added", "removed", "changed"):
            m = re.match(r"^([fdlbcps][^:]+):\s+(.+)$", s)
            if m:
                flags = m.group(1).strip()
                path = m.group(2).strip()
                entry = {"path": path, "flags": flags}
                if section == "added":
                    result["added_entries"].append(entry)
                elif section == "removed":
                    result["removed_entries"].append(entry)
                elif section == "changed":
                    result["changed_entries"].append(entry)
            continue

        # Detailed change lines
        if section == "detail":
            # File: /path  or  Directory: /path  or  Link: /path
            m = re.match(r"^(File|Directory|Link):\s+(.+)$", s)
            if m:
                current_file = m.group(2).strip()
                current_hash_name = None
                continue
            # Attribute: old_value | new_value  (with potential multi-line hashes)
            m = re.match(r"^(\w+)\s*:\s+(.+)$", s)
            if m and current_file:
                attr = m.group(1).strip()
                val_part = m.group(2).strip()
                if "|" in val_part:
                    vals = val_part.split("|", 1)
                    if len(vals) >= 2:
                        change = {
                            "path": current_file,
                            "attribute": attr,
                            "old": vals[0].strip(),
                            "new": vals[1].strip(),
                        }
                        result["detailed_changes"].append(change)
                        current_hash_name = attr
                continue
            # Continuation of multi-line hash value
            if current_hash_name and current_file and result["detailed_changes"]:
                last = result["detailed_changes"][-1]
                if last["attribute"] == current_hash_name:
                    if "|" in s:
                        parts = s.split("|", 1)
                        if len(parts) == 2:
                            last["old"] += parts[0].strip()
                            last["new"] += parts[1].strip()
                    else:
                        pass
                continue

        # Database hashes
        if section == "databases":
            # New database file path (starts with /)
            if s.startswith("/"):
                current_db = s
                result["databases"][current_db] = {}
                current_hash_name = None
                continue
            # Hash line: "SHA256    : base64value"
            m = re.match(r"^(\w+)\s*:\s+(.+)$", s)
            if m and current_db:
                current_hash_name = m.group(1)
                result["databases"][current_db][current_hash_name] = m.group(2).strip()
                continue
            # Continuation of multi-line hash value
            if current_db and current_hash_name:
                result["databases"][current_db][current_hash_name] += s
                continue

    # Clean up empty collections
    for key in ("added_entries", "removed_entries", "changed_entries", "detailed_changes"):
        if not result[key]:
            del result[key]

    if not result["summary"]:
        del result["summary"]

    if not result["databases"]:
        del result["databases"]

    if result["outline"] is None:
        del result["outline"]

    if result["run_time_seconds"] is None:
        del result["run_time_seconds"]

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
