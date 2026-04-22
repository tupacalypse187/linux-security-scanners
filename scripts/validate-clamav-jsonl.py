#!/usr/bin/env python3
"""Validate ClamAV JSONL output for CI smoke tests."""
import json, sys

path = sys.argv[1] if len(sys.argv) > 1 else "/var/log/clamav/clamscan.jsonl"

with open(path) as f:
    lines = f.readlines()

expected = int(sys.argv[2]) if len(sys.argv) > 2 else 2

if len(lines) != expected:
    print("ERROR: Expected {} JSONL lines, got {}".format(expected, len(lines)))
    sys.exit(1)

for i, line in enumerate(lines, 1):
    try:
        obj = json.loads(line)
        hostname = obj.get("hostname", "MISSING")
        nfiles = len(obj.get("file_results", []))
        print("Line {}: OK (hostname={}, files={})".format(i, hostname, nfiles))
    except Exception as e:
        print("Line {}: INVALID JSON - {}".format(i, e))
        sys.exit(1)

print("All {} lines valid.".format(len(lines)))
