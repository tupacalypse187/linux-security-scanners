#!/usr/bin/env python3
"""Validate AIDE JSONL output for CI smoke tests."""
import json, sys

path = sys.argv[1] if len(sys.argv) > 1 else "/var/log/aide/aide.jsonl"

with open(path) as f:
    lines = f.readlines()

expected = int(sys.argv[2]) if len(sys.argv) > 2 else 2

if len(lines) != expected:
    print("ERROR: Expected {} JSONL lines, got {}".format(expected, len(lines)))
    sys.exit(1)

for i, line in enumerate(lines, 1):
    try:
        obj = json.loads(line)
        assert "scanner" in obj and obj["scanner"] == "aide"
        assert "result" in obj
        assert "hostname" in obj
        assert "timestamp" in obj
        print("Line {}: OK (result={}, hostname={})".format(i, obj["result"], obj["hostname"]))
    except Exception as e:
        print("Line {}: INVALID - {}".format(i, e))
        sys.exit(1)

print("All {} lines valid.".format(len(lines)))
