# AIDE Output Comparison: Native JSON vs Python Wrapper (AL2023)

> Tested on: `amazonlinux:2023` with AIDE 0.18.6, single tampered file (`/etc/passwd`)
> Date: 2026-04-23

---

## Side-by-Side Summary

| Aspect | Native `report_format=json` | Python Wrapper (`aide-to-json.py`) |
|--------|-----------------------------|-------------------------------------|
| **Format** | Pretty-printed JSON (687 lines) | Single-line JSONL (1 line per check) |
| **Size** | 18 KB | 12.5 KB per line |
| **OS Support** | AL2023 only (AIDE 0.18+) | All three OSes (AL9, AL2, AL2023) |
| **Hostname** | No | Yes (`"hostname": "0d15bb47ec3a"`) |
| **Timestamp** | `start_time` / `end_time` (AIDE's own) | ISO 8601 `timestamp` field added |
| **Scanner tag** | No | Yes (`"scanner": "aide"`) |
| **JSONL append** | No (prints to stdout) | Yes (appends to `/var/log/aide/aide.jsonl`) |
| **SIEM log-shipper friendly** | No — multi-line breaks line-oriented tailing | Yes — one object per line |
| **Config complexity** | Order-sensitive in `aide.conf` (must precede `report_url=`), or use `-B` CLI flag | No config changes needed — pipes from text output |
| **Added files** | `"added"` section with flag strings | Not included |
| **Changed files** | `"changed"` section with compact flag strings + `"details"` with nested `{old, new}` per attribute | `"detailed_changes"` flat array of `{path, attribute, old, new}` objects |
| **Database hashes** | Yes — full `"databases"` section with all hash algorithms | No |
| **Exit code** | 5 (changes detected) — same | 5 (AIDE's exit code, wrapper doesn't change it) |

---

## Schema Comparison

### Native AIDE JSON (structure)

```json
{
  "start_time": "2026-04-23 10:36:24 +0000",
  "aide_version": "0.18.6",
  "outline": "AIDE found differences between database and filesystem!!",
  "number_of_entries": { "total": 8299, "added": 1, "removed": 0, "changed": 60 },
  "added": { "/etc/hostname": "f++++++++++++++++" },
  "changed": { "/etc/passwd": "f > ... mc..H..  ", ... },
  "details": {
    "/etc/passwd": {
      "size":      { "old": 533, "new": 542 },
      "modify_time": { "old": "2023-01-30 ...", "new": "2026-04-23 ..." },
      "sha256":    { "old": "0Tf6i/...", "new": "kOZtzo..." }
    }
  },
  "databases": { "/var/lib/aide/aide.db.gz": { "md5": "...", "sha256": "...", ... } },
  "end_time": "2026-04-23 10:36:28 +0000",
  "run_time_seconds": 4
}
```

### Python Wrapper JSONL (structure)

```json
{
  "result": "changes_detected",
  "summary": { "total_entries": 8299, "added": 1, "removed": 0, "changed": 60 },
  "detailed_changes": [
    { "path": "/etc/passwd", "attribute": "Size", "old": "533", "new": "542" },
    { "path": "/etc/passwd", "attribute": "SHA256", "old": "0Tf6i/...", "new": "kOZtzo..." }
  ],
  "hostname": "0d15bb47ec3a",
  "timestamp": "2026-04-23T10:36:37Z",
  "scanner": "aide"
}
```

---

## What the Native Output Has That the Wrapper Doesn't

1. **`added` section** — lists newly appeared files with AIDE flag strings (e.g. `"f++++++++++++++++"`)
2. **`databases` section** — integrity hashes of the AIDE baseline database itself (md5, sha256, sha512, whirlpool, gost, stribog256, stribog512, etc.)
3. **`changed` flag strings** — compact AIDE notation like `"f > ... mc..H..  "` showing which attribute groups changed
4. **`outline` message** — human-readable status line (`"AIDE found differences between database and filesystem!!"`)
5. **`run_time_seconds`** — explicit scan duration

## What the Wrapper Has That Native Doesn't

1. **`hostname`** — which host produced this result (critical for multi-host SIEM correlation)
2. **`timestamp`** — ISO 8601 timestamp added at parse time (native only has AIDE's internal `start_time`/`end_time`)
3. **`scanner`** — identifies the scanner type (useful when multiple scanner types feed the same SIEM index)
4. **JSONL format** — single-line output, appendable to a log file, tailable by Filebeat/Fluentd/rsyslog
5. **Flat `detailed_changes` array** — easier to query with jq/SIEM filters: `jq '.detailed_changes[] | select(.path == "/etc/passwd")'`

---

## Assessment

### When to use native JSON

If you're on AL2023-only infrastructure and need:
- Self-contained database integrity verification (hashes of the AIDE DB itself)
- AIDE's compact flag notation for quick visual triage
- No additional dependencies beyond AIDE itself

Use via: `aide --check -B 'report_format=json'`

### When to use the Python wrapper (recommended)

For any SIEM/multi-host deployment:
- **Cross-OS consistency** — same JSON schema whether the host runs AL9, AL2, or AL2023
- **SIEM-ready** — one line per check, no multi-line parsing needed
- **Host correlation** — `hostname` + `timestamp` fields let you query across hosts in Elasticsearch/Splunk
- **Log rotation** — appends to a JSONL file with logrotate config (30-day retention)
- **No config gotchas** — no risk of misordering `report_format` vs `report_url` in `aide.conf`

The wrapper sacrifices the `added` files section, database hashes, and AIDE flag strings — but these are low-value for automated SIEM alerting compared to having a uniform, host-enriched, single-line format across all OSes.

### Recommendation

**Keep the Python wrapper as the default pipeline for all OSes.** The native `report_format=json` is a good validation tool and is now tested in CI, but the wrapper's cross-OS uniformity and SIEM-friendly format make it the right production choice. The native JSON option exists as a fallback for AL2023-only environments that want zero-dependency output.

---

*Generated from live Docker test on 2026-04-23. Both outputs captured from the same image with the same tamper applied (`echo "tampered" >> /etc/passwd`).*
