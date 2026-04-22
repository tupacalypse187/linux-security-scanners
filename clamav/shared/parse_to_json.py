#!/usr/bin/env python3
import json, re
from datetime import datetime

def parse_clamscan(raw):
    result = {"file_results": [], "scan_summary": {}}
    in_summary = False

    for line in raw.splitlines():
        line = line.strip()

        if "--- SCAN SUMMARY ---" in line:
            in_summary = True
            continue

        if not in_summary:
            # file results: /path: STATUS
            m = re.match(r"^(.+?):\s+(OK|FOUND|ERROR.*)$", line)
            if m:
                result["file_results"].append({
                    "file": m.group(1).strip(),
                    "status": m.group(2).strip()
                })
        else:
            # summary fields: Key: Value
            m2 = re.match(r"^([\w\s]+?):\s+(.+)$", line)
            if m2:
                key = m2.group(1).strip().lower().replace(" ", "_")
                val = m2.group(2).strip()
                result["scan_summary"][key] = val

    if not result["scan_summary"]:
        del result["scan_summary"]

    return result

# Read raw outputs
with open("/tmp/with_summary.txt") as f:
    with_raw = f.read()

with open("/tmp/no_summary.txt") as f:
    no_raw = f.read()

with_json = parse_clamscan(with_raw)
no_json = parse_clamscan(no_raw)

with_json["run_type"] = "with_summary"
no_json["run_type"] = "no_summary"

host = open("/etc/hostname").read().strip()
ts = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
for obj in [with_json, no_json]:
    obj["hostname"] = host
    obj["timestamp"] = ts

with open("/output/clamscan-json.txt", "w") as f:
    f.write("=== WITH summary (1 JSON line) ===" + "\n")
    f.write(json.dumps(with_json, separators=(",", ":")) + "\n")
    f.write("\n=== WITHOUT summary --no-summary (1 JSON line) ===" + "\n")
    f.write(json.dumps(no_json, separators=(",", ":")) + "\n")
    f.write("\n=== Pretty-printed for readability ===" + "\n")
    f.write("\nWITH summary:\n")
    f.write(json.dumps(with_json, indent=2) + "\n")
    f.write("\nWITHOUT summary:\n")
    f.write(json.dumps(no_json, indent=2) + "\n")
