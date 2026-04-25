Both `clamscan-to-json.py` and `aide-to-json.py` emit **one compact JSON object per line** to JSONL files (`/var/log/clamav/clamscan.jsonl` and `/var/log/aide/aide.jsonl` respectively). This design makes `jq` — the command-line JSON processor — the natural tool for ad-hoc investigation, alerting pipelines, and SIEM pre-filtering. This page provides a systematic catalog of production-grade `jq` queries organized by scanner, use case, and complexity, with every expression verified against the actual schemas emitted by the parsers.

Sources: [clamscan-to-json.py](clamav/shared/clamscan-to-json.py#L9-L11) · [aide-to-json.py](aide/shared/aide-to-json.py#L7-L10)

## JSONL Fundamentals: Reading the Log Files

Each scanner appends one JSON object per invocation to its JSONL file. The serializers use `separators=(",", ":")` to produce the most compact representation — no indentation, no extraneous whitespace. Because each line is a self-contained JSON object, `jq` can process lines independently with no need for slurping or array wrapping.

The two JSONL log paths you'll query in production are:

| Scanner | JSONL Path | Rotate Config |
|---------|-----------|---------------|
| ClamAV | `/var/log/clamav/clamscan.jsonl` | [clamav-jsonl.conf](clamav/shared/clamav-jsonl.conf#L1-L13) |
| AIDE | `/var/log/aide/aide.jsonl` | [aide-jsonl.conf](aide/shared/aide-jsonl.conf#L1-L10) |

The most basic `jq` invocation against a JSONL file processes each line independently and pretty-prints the result:

```bash
# Pretty-print all ClamAV scan results
jq '.' /var/log/clamav/clamscan.jsonl

# Pretty-print all AIDE check results
jq '.' /var/log/aide/aide.jsonl
```

To process only a specific line (e.g., the most recent scan), use `tail` to isolate it before piping to `jq`:

```bash
# Most recent ClamAV scan
tail -1 /var/log/clamav/clamscan.jsonl | jq '.'

# Most recent AIDE check
tail -1 /var/log/aide/aide.jsonl | jq '.'
```

Sources: [clamscan-to-json.py](clamav/shared/clamscan-to-json.py#L64-L67) · [aide-to-json.py](aide/shared/aide-to-json.py#L214-L216)

## ClamAV Queries

The ClamAV JSON schema has a predictable envelope: `file_results` (array of `{file, status}` objects), an optional `scan_summary` object, and two metadata fields (`hostname`, `timestamp`). The queries below target the most common operational questions.

Sources: [clamscan-to-json.py](clamav/shared/clamscan-to-json.py#L17-L51) · [ClamAV JSON Schema and Output Formats](7-clamav-json-schema-and-output-formats)

### Quick Health Check: Extract the Scan Verdict

The fastest way to determine whether any scan found threats is to check `scan_summary.infected_files`:

```bash
tail -1 /var/log/clamav/clamscan.jsonl | jq '.scan_summary.infected_files'
# Output: 0
```

To get the verdict alongside context (hostname, scan time, file count) in a compact summary:

```bash
tail -1 /var/log/clamav/clamscan.jsonl | jq '{
  host: .hostname,
  time: .timestamp,
  infected: .scan_summary.infected_files,
  scanned: .scan_summary.scanned_files,
  engine: .scan_summary.engine_version
}'
```

Output:

```json
{
  "host": "d9cb8b2b07e0",
  "time": "2026-04-23T13:58:20Z",
  "infected": 0,
  "scanned": 4,
  "engine": "1.5.2"
}
```

Sources: [clamscan-to-json.py](clamav/shared/clamscan-to-json.py#L36-L46) · [clamav/amazonlinux2023/results/clamscan.json](clamav/amazonlinux2023/results/clamscan.json#L1-L6)

### Finding Infected Files Across All Scans

The most critical operational query — extract every infected file from the entire JSONL history:

```bash
jq '.file_results[] | select(.status != "OK")' /var/log/clamav/clamscan.jsonl
```

This filters `file_results` for entries whose `status` is not `"OK"`. Because ClamAV produces `"FOUND <signature>"` for detections, this catches all variants. To include the hostname and timestamp context:

```bash
jq '{host: .hostname, time: .timestamp, file: .file_results[] | select(.status != "OK")}' \
  /var/log/clamav/clamscan.jsonl
```

For a compact list of just the file paths and their signatures across all historical scans:

```bash
jq -r '[.file_results[] | select(.status != "OK")] | .[] | "\(.file)\t\(.status)"' \
  /var/log/clamav/clamscan.jsonl
```

Sources: [clamscan-to-json.py](clamav/shared/clamscan-to-json.py#L29-L34)

### Extracting Scan Metadata and Performance Metrics

To build a scan-duration dashboard from historical data, extract `time`, `data_scanned`, and `engine_version` from all entries that have a `scan_summary`:

```bash
jq -r 'select(.scan_summary) |
  [.timestamp, .hostname, .scan_summary.time, .scan_summary.scanned_files, .scan_summary.engine_version] |
  @tsv' /var/log/clamav/clamscan.jsonl
```

The `-r` flag with `@tsv` produces tab-separated output suitable for piping into `awk` or spreadsheet tools:

```
2026-04-23T13:56:50Z  ae1e553cdb71   7.181 sec (0 m 7 s)    4       1.5.2
2026-04-24T09:12:33Z  web-prod-02    42.873 sec (0 m 42 s)  1284    1.5.2
```

Sources: [clamscan-to-json.py](clamav/shared/clamscan-to-json.py#L36-L46)

### Per-File Status Report

To produce a table of every scanned file and its status from the most recent scan:

```bash
tail -1 /var/log/clamav/clamscan.jsonl | jq -r '.file_results[] | "\(.file)\t\(.status)"'
```

Output:

```
/etc/hostname   OK
/etc/hosts      OK
/etc/passwd     OK
/etc/resolv.conf        OK
```

Sources: [clamscan-to-json.py](clamav/shared/clamscan-to-json.py#L29-L34) · [clamav/almalinux9/results/clamscan.json](clamav/almalinux9/results/clamscan.json#L1-L6)

### Alerting: Detect Any Non-Zero Infection Count

For integration with cron-based alerting or monitoring hooks, use `jq`'s exit-code behavior — `-e` flag sets exit code based on the result:

```bash
# Returns exit code 1 if any scan has infected files > 0
jq -e '[.[] | select(.scan_summary.infected_files > 0)] | length > 0' \
  <(tail -20 /var/log/clamav/clamscan.jsonl | jq -s '.')
```

A simpler variant for monitoring the most recent scan:

```bash
tail -1 /var/log/clamav/clamscan.jsonl | \
  jq -e '.scan_summary.infected_files > 0'
```

This exits with code `0` (true) when infections are found and `1` (false) when clean — invert the logic depending on your alerting convention.

Sources: [clamscan-to-json.py](clamav/shared/clamscan-to-json.py#L41-L42)

## AIDE Queries

AIDE's JSON output is substantially richer than ClamAV's, with nested arrays for added/removed/changed entries, a flat `detailed_changes` array, and database hash information. The flat denormalized design of `detailed_changes` was chosen specifically to make `jq` filtering straightforward — every change object carries its full context (`path`, `attribute`, `old`, `new`) without requiring nested traversal.

Sources: [aide-to-json.py](aide/shared/aide-to-json.py#L114-L162) · [AIDE JSON Schema and Output Fields Reference](11-aide-json-schema-and-output-fields-reference)

### Quick Health Check: Clean vs. Changes Detected

The `result` field provides an immediate binary verdict:

```bash
tail -1 /var/log/aide/aide.jsonl | jq '{result: .result, host: .hostname, time: .timestamp}'
```

Output:

```json
{
  "result": "changes_detected",
  "host": "d9cb8b2b07e0",
  "time": "2026-04-23T13:58:37Z"
}
```

To count how many checks in the entire JSONL history detected changes:

```bash
jq -s '[.[] | select(.result == "changes_detected")] | length' \
  /var/log/aide/aide.jsonl
```

The `-s` (slurp) flag reads all lines into a single array, enabling aggregation across scan history.

Sources: [aide-to-json.py](aide/shared/aide-to-json.py#L23-L24) · [aide-to-json.py](aide/shared/aide-to-json.py#L44-L50)

### Listing All Changed, Added, and Removed Files

Each entry category has its own top-level array. Extract the changed file paths from the most recent check:

```bash
tail -1 /var/log/aide/aide.jsonl | jq -r '.changed_entries[]? | .path'
```

The `?` operator safely handles cases where `changed_entries` is absent (i.e., clean scans where the parser deletes the empty array). To get all modifications across all three categories in a unified view:

```bash
tail -1 /var/log/aide/aide.jsonl | jq '{
  added:   [.added_entries[]?.path],
  removed: [.removed_entries[]?.path],
  changed: [.changed_entries[]?.path]
}'
```

Output from a tampered check on Amazon Linux 2023:

```json
{
  "added": [
    "/etc/hostname",
    "/var/log/aide/aide.jsonl"
  ],
  "removed": [],
  "changed": [
    "/etc/hosts",
    "/etc/resolv.conf"
  ]
}
```

Sources: [aide-to-json.py](aide/shared/aide-to-json.py#L97-L111) · [aide/amazonlinux2023/results/aide.json](aide/amazonlinux2023/results/aide.json#L1-L6)

### Drilling Into Detailed Attribute Changes

The `detailed_changes` flat array is where `jq` delivers the most value for AIDE. Each object is a self-contained `{path, attribute, old, new}` record. To see every attribute change for a specific file:

```bash
tail -1 /var/log/aide/aide.jsonl | \
  jq '.detailed_changes[]? | select(.path == "/etc/resolv.conf")'
```

To extract only permission changes across all files (a common forensic signal):

```bash
tail -1 /var/log/aide/aide.jsonl | \
  jq '.detailed_changes[]? | select(.attribute == "Perm")'
```

For a compact diff-style report of all changes:

```bash
tail -1 /var/log/aide/aide.jsonl | jq -r '
  .detailed_changes[]? |
  "\(.path)  \(.attribute): \(.old) → \(.new)"
'
```

Sample output:

```
/etc/resolv.conf  Size: 24 → 222
/etc/resolv.conf  Perm: -rw-r--r-- → -rwxrwxrwx
/etc/resolv.conf  Ctime: 2026-04-23 13:56:50 +0000 → 2026-04-23 13:58:30 +0000
/etc/resolv.conf  SHA512: 3UdehPxb... → gbwQk3n0...
```

Sources: [aide-to-json.py](aide/shared/aide-to-json.py#L138-L147) · [native-json-comparison.md](aide/amazonlinux2023/native-json-comparison.md#L56-L83)

### Summary Statistics Across Historical Checks

To aggregate change counts over time, combine `-s` (slurp mode) with array construction:

```bash
jq -s '
  map({
    time: .timestamp,
    host: .hostname,
    changed: (.changed_entries // [] | length),
    added:   (.added_entries // [] | length),
    removed: (.removed_entries // [] | length)
  })
' /var/log/aide/aide.jsonl
```

The `// []` alternative operator handles lines where the parser deleted empty arrays — it substitutes an empty array so `.length` always works. Output for a 2-entry JSONL file:

```json
[
  {
    "time": "2026-04-23T13:58:30Z",
    "host": "d9cb8b2b07e0",
    "changed": 24,
    "added": 1,
    "removed": 0
  },
  {
    "time": "2026-04-23T13:58:37Z",
    "host": "d9cb8b2b07e0",
    "changed": 24,
    "added": 2,
    "removed": 0
  }
]
```

Sources: [aide-to-json.py](aide/shared/aide-to-json.py#L59-L68) · [aide-to-json.py](aide/shared/aide-to-json.py#L183-L198)

### Alerting: Detect Permission or Ownership Changes

Permission modifications (`Perm`, `UID`, `GID`) are high-signal forensic indicators. To alert on any such change in the most recent check:

```bash
tail -1 /var/log/aide/aide.jsonl | \
  jq -e '[.detailed_changes[]? | .attribute] | any(. == "Perm" or . == "UID" or . == "GID")'
```

For a richer alert that shows *what* changed, not just whether something changed:

```bash
tail -1 /var/log/aide/aide.jsonl | \
  jq '.detailed_changes[]? | select(.attribute == "Perm" or .attribute == "UID" or .attribute == "GID") |
      {path, attribute, old, new}'
```

Sources: [aide-to-json.py](aide/shared/aide-to-json.py#L138-L147)

### Extracting Database Integrity Hashes

The `databases` object maps database file paths to their hash algorithms and base64 digests. To verify the AIDE database hasn't been tampered with by extracting and comparing hashes:

```bash
tail -1 /var/log/aide/aide.jsonl | \
  jq '.databases // {} | to_entries[] | {db: .key, hashes: .value}'
```

Output from Amazon Linux 2023 (which reports the broadest algorithm set):

```json
{
  "db": "/var/lib/aide/aide.db.gz",
  "hashes": {
    "MD5": "mYEyR1RXlI0Cj8au2xfgLw==",
    "SHA256": "hk+lBe1luaqf+o1PhASgtSiETb980js9YbhjXWrJgI4=",
    "SHA512": "nN/gW+89fMrXAqZOLW/6cqX/yEERbmeKveT8QAXe4SA..."
  }
}
```

To compare SHA256 hashes between two consecutive checks (detecting database replacement):

```bash
jq -s '
  (.[0].databases // {} | .[] | .SHA256) as $old |
  (.[1].databases // {} | .[] | .SHA256) as $new |
  {old_sha256: $old, new_sha256: $new, match: ($old == $new)}
' <(head -1 /var/log/aide/aide.jsonl) <(tail -1 /var/log/aide/aide.jsonl)
```

Sources: [aide-to-json.py](aide/shared/aide-to-json.py#L164-L181) · [native-json-comparison.md](aide/amazonlinux2023/native-json-comparison.md#L73-L77)

## Cross-Scanner Queries

Because both scanners share the same metadata envelope (`hostname`, `timestamp`) and the `scanner` field identifies the source, you can merge JSONL files from both scanners into a unified timeline. This is useful for correlated incident investigation — seeing ClamAV detections alongside AIDE changes on the same host.

Sources: [clamscan-to-json.py](clamav/shared/clamscan-to-json.py#L61-L62) · [aide-to-json.py](aide/shared/aide-to-json.py#L210-L213)

### Unified Timeline of All Security Events

```bash
cat /var/log/clamav/clamscan.jsonl /var/log/aide/aide.jsonl | \
  jq -s 'sort_by(.timestamp) | .[] | {scanner, time: .timestamp, host: .hostname}'
```

The `-s` flag slurps all lines from both files into one array, `sort_by(.timestamp)` orders them chronologically, and the projection strips each event to its essentials. Output:

```json
{
  "scanner": "clamav",
  "time": "2026-04-23T13:58:20Z",
  "host": "d9cb8b2b07e0"
}
{
  "scanner": "aide",
  "time": "2026-04-23T13:58:30Z",
  "host": "d9cb8b2b07e0"
}
```

### Per-Host Event Count by Scanner Type

```bash
cat /var/log/clamav/clamscan.jsonl /var/log/aide/aide.jsonl | \
  jq -s 'group_by(.hostname) | map({
    host: .[0].hostname,
    clamav: [.[] | select(.scanner == "clamav")] | length,
    aide:   [.[] | select(.scanner == "aide")]   | length
  })'
```

Sources: [validate-aide-jsonl.py](scripts/validate-aide-jsonl.py#L16-L26) · [validate-clamav-jsonl.py](scripts/validate-clamav-jsonl.py#L16-L24)

## Advanced Patterns

### Combining jq with Journalctl

When the systemd service captures parser output to the journal (as designed in [Systemd Service and Timer Units for Scheduled Scans](13-systemd-service-and-timer-units-for-scheduled-scans)), you can query directly from `journalctl` without reading the JSONL file:

```bash
# Extract AIDE JSON from the systemd journal
journalctl -u aide-check.service --since "today" -o cat | jq '.'

# Alert on AIDE changes detected in the last hour
journalctl -u aide-check.service --since "1 hour ago" -o cat | \
  jq -e 'select(.result == "changes_detected") | {time: .timestamp, changed: [.changed_entries[]?.path]}'
```

The `-o cat` flag strips journal metadata, leaving only the JSON payload that the parser wrote to stdout.

Sources: [aide-to-json.py](aide/shared/aide-to-json.py#L216-L217) · [clamscan-to-json.py](clamav/shared/clamscan-to-json.py#L66-L67)

### Querying Compressed Rotated Logs

Logrotate compresses old JSONL files (controlled by the `compress` directive in both [clamav-jsonl.conf](clamav/shared/clamav-jsonl.conf#L1-L13) and [aide-jsonl.conf](aide/shared/aide-jsonl.conf#L1-L10)). To query across both current and rotated logs:

```bash
# Query all ClamAV scan history including compressed rotations
zcat /var/log/clamav/clamscan.jsonl.*.gz 2>/dev/null; cat /var/log/clamav/clamscan.jsonl | \
  jq -s 'map(select(.scan_summary.infected_files > 0)) | length'
```

The `zcat` decompresses all `.gz` rotated files, `2>/dev/null` suppresses errors when no rotated files exist, and `cat` appends the current (uncompressed) log. Piped together into `jq -s`, they form a single array spanning the full retention period.

### Slurp Mode vs. Line-by-Line Processing

Understanding when to use `-s` (slurp) versus line-by-line processing is critical for correct results with JSONL files. The following table summarizes the trade-off:

| Pattern | Use When | Example |
|---------|----------|---------|
| `jq '.'` (default) | Transforming or filtering individual lines independently | Extract a field from each scan |
| `jq -s '.'` | Aggregating across multiple lines (counting, sorting, grouping) | Count total infected files across all scans |
| `jq -s 'sort_by(...)'` | Ordering events by a field | Unified chronological timeline |
| `tail -N | jq '.'` | Processing the last *N* scans | Most recent scan summary |
| `head -N | jq '.'` | Processing the first *N* scans (oldest) | Baseline comparison |

Line-by-line processing is more memory-efficient for large JSONL files because `jq` never holds the entire file in memory. Slurp mode is necessary only when the query requires cross-line context.

Sources: [clamscan-to-json.py](clamav/shared/clamscan-to-json.py#L64-L67) · [aide-to-json.py](aide/shared/aide-to-json.py#L214-L216)

## Query Quick Reference

The following table collects the most frequently used `jq` expressions for both scanners, ready to copy into scripts or terminal sessions.

| Goal | Command |
|------|---------|
| **ClamAV: infected file count** | `tail -1 /var/log/clamav/clamscan.jsonl \| jq '.scan_summary.infected_files'` |
| **ClamAV: list infected files** | `jq '.file_results[] \| select(.status != "OK")' /var/log/clamav/clamscan.jsonl` |
| **ClamAV: engine version** | `tail -1 /var/log/clamav/clamscan.jsonl \| jq '.scan_summary.engine_version'` |
| **ClamAV: full summary** | `tail -1 /var/log/clamav/clamscan.jsonl \| jq '.scan_summary'` |
| **AIDE: clean or changed?** | `tail -1 /var/log/aide/aide.jsonl \| jq '.result'` |
| **AIDE: changed file paths** | `tail -1 /var/log/aide/aide.jsonl \| jq -r '.changed_entries[]?.path'` |
| **AIDE: added file paths** | `tail -1 /var/log/aide/aide.jsonl \| jq -r '.added_entries[]?.path'` |
| **AIDE: detailed changes for a path** | `tail -1 /var/log/aide/aide.jsonl \| jq '.detailed_changes[]? \| select(.path == "/etc/resolv.conf")'` |
| **AIDE: permission changes only** | `tail -1 /var/log/aide/aide.jsonl \| jq '.detailed_changes[]? \| select(.attribute == "Perm")'` |
| **AIDE: run time** | `tail -1 /var/log/aide/aide.jsonl \| jq '.run_time_seconds'` |
| **AIDE: change summary counts** | `tail -1 /var/log/aide/aide.jsonl \| jq '.summary'` |
| **AIDE: DB hashes** | `tail -1 /var/log/aide/aide.jsonl \| jq '.databases'` |
| **Both: unified timeline** | `cat /var/log/clamav/clamscan.jsonl /var/log/aide/aide.jsonl \| jq -s 'sort_by(.timestamp) \| .[] \| {scanner, time: .timestamp, host: .hostname}'` |
| **Both: events from a specific host** | `cat /var/log/clamav/clamscan.jsonl /var/log/aide/aide.jsonl \| jq 'select(.hostname == "web-prod-02")'` |

Sources: [clamscan-to-json.py](clamav/shared/clamscan-to-json.py#L17-L51) · [aide-to-json.py](aide/shared/aide-to-json.py#L21-L200)

## Next Steps

- For the complete field-by-field schema these queries target, see [ClamAV JSON Schema and Output Formats](7-clamav-json-schema-and-output-formats) and [AIDE JSON Schema and Output Fields Reference](11-aide-json-schema-and-output-fields-reference).
- For the log rotation and SIEM shipper configuration that determines how these JSONL files grow and are consumed, see [JSONL Log Format, Logrotate, and Log Shipper Configuration](12-jsonl-log-format-logrotate-and-log-shipper-configuration).
- For the systemd units that schedule scans and write these JSONL files, see [Systemd Service and Timer Units for Scheduled Scans](13-systemd-service-and-timer-units-for-scheduled-scans).