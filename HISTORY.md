# Project history — PRs and issues

This repository is a mirror of a public GitHub repo (originally `tupacalypse187/linux-security-scanners`). All commits — including merge commits that reference PR numbers — are present in git history. PR descriptions and issue writeups, however, live in GitHub's database and don't travel over `git push`. This file transcribes them so the rationale stays with the code.

The original PR / issue numbers are preserved below as `#N` for traceability. Where a PR closes an issue, the issue is listed immediately after its PR.

## Timeline

| # | Title | Merged / Closed | Commit |
|---|---|---|---|
| PR #1 | ⬆️ feat: unify ClamAV to 1.5.2 across all OSes via Cisco Talos RPM | 2026-04-22T13:51:10Z | `2e00f03e30` |
| PR #2 | 🐛 fix: correct the claim about report_format=json on Amazon Linux 2023 | 2026-04-22T15:32:15Z | `54e54ec1f9` |
| PR #3 | 📝 docs: add AIDE native JSON vs wrapper comparison, fix shell script line endings | 2026-04-23T10:58:10Z | `a6159a25ec` |
| PR #4 | ✅ test: add repeatable test script and sample results for all scanner/OS combos | 2026-04-23T11:40:45Z | `1a5af8dd65` |
| PR #5 | 👷 ci: upload sample scan results as downloadable artifacts | 2026-04-23T11:59:44Z | `fea36ffb90` |
| PR #6 | ✨ feat: achieve feature parity between AIDE parser and native JSON output | 2026-04-23T13:14:57Z | `f68a02b841` |
| PR #7 | 🐛 fix: portable run-tests.sh quoting + native ARM64 ClamAV support | 2026-04-23T14:11:47Z | `0dc14ae04d` |
| PR #9 | 🐛 fix: parse multi-line ACL values correctly in aide-to-json.py (#8) | 2026-04-23T14:29:04Z | `49b1fc3c41` |
| PR #11 | ✨ feat: add automated test results report generator | 2026-04-24T11:43:23Z | `7a94d32dc4` |
| PR #12 | 📝 docs: add PR #11 to HISTORY.md | 2026-04-24T18:50:41Z | `a93c0d1005` |
| PR #13 | 📝 docs: add Zread CLI wiki and documentation references | 2026-04-25T09:56:58Z | `c6f11551a7` |
| Issue #8 | 🐛 aide-to-json.py misparses multi-line ACL continuations | 2026-04-23T14:29:05Z | — |

---

## PR #1 — ⬆️ feat: unify ClamAV to 1.5.2 across all OSes via Cisco Talos RPM

**Merged:** 2026-04-22T13:51:10Z · **Commit:** `2e00f03e30`

## 📝 Summary

Standardizes ClamAV to version 1.5.2 across all three OS images by replacing the EPEL packages (AlmaLinux 9, Amazon Linux 2) with the Cisco Talos RPM that was already used for Amazon Linux 2023.

## 🔄 Changes

- 🐧 **AlmaLinux 9 Dockerfile** — Replaced `epel-release` + `dnf install clamav` with Cisco Talos RPM download, added `shadow-utils`, `useradd`, `freshclam.conf` creation
- 🐧 **Amazon Linux 2 Dockerfile** — Replaced `amazon-linux-extras epel` + `yum install clamav` with Cisco Talos RPM download, added `shadow-utils`, `useradd`, `freshclam.conf` creation
- 🔧 **clamav-scan.service** — Updated binary paths from `/usr/bin/` to `/usr/local/bin/` for `freshclam` and `clamscan` (Cisco RPM installs to `/usr/local/` prefix)
- ⏰ **aide-check.timer** — Changed from daily at 2am (2h jitter) to every 4 hours (30m jitter) for more frequent integrity checks
- 📝 **README.md** — Updated version table, OS comparison matrix, gotchas section, example outputs, and file tree to reflect unified 1.5.2
- 📝 **clamav/README.md** — Updated all version references, comparison table, Dockerfile examples, systemd paths, and test expected outputs
- 📝 **aide/README.md** — Updated timer documentation to reflect new 4-hour schedule
- 📝 **CLAUDE.md** — Updated project structure, key findings table, and Dockerfile descriptions

## ✅ Verification

```bash
# Build and test all three images
docker build -t almalinux9-clamav:latest -f clamav/almalinux9/Dockerfile .
docker build -t amazonlinux2-clamav:latest -f clamav/amazonlinux2/Dockerfile .
docker build -t amazonlinux2023-clamav:latest -f clamav/amazonlinux2023/Dockerfile .

# Verify version on each
docker run --rm almalinux9-clamav:latest clamscan --version
docker run --rm amazonlinux2-clamav:latest clamscan --version
docker run --rm amazonlinux2023-clamav:latest clamscan --version
# All should report ClamAV 1.5.2
```

CI will also validate via `.github/workflows/ci.yml` which builds all images and runs smoke tests.

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)

---

## PR #2 — 🐛 fix: correct the claim about report_format=json on Amazon Linux 2023

**Merged:** 2026-04-22T15:32:15Z · **Commit:** `54e54ec1f9`

## 📝 Summary

Corrects a factual error in the docs. AIDE 0.18.6 on Amazon Linux 2023 **does** support `report_format=json` — the earlier claim that it was accepted but non-functional was based on a test that placed the directive in the wrong spot in `aide.conf`. The JSON reporter works; the directive is just order-sensitive.

## 🔍 Root Cause

AIDE applies `report_format` to each `report_url` **at the moment the URL is declared**, not globally. The default `/etc/aide.conf` on AL2023 declares its two `report_url=` lines early (around line 21–22):

```
report_url=file:@@{LOGDIR}/aide.log
report_url=stdout
```

Appending `report_format=json` to the **end** of the file arrives *after* both URLs are already bound to the default `plain` format — so the scan still emits plain text. Move the directive *before* the `report_url=` lines (or pass it via `-B` on the CLI) and native JSON works.

Verified on AL2023 / AIDE 0.18.6:

| Approach | Result |
|---|---|
| `aide --check -B 'report_format=json'` | ✅ JSON |
| `report_format=json` inserted BEFORE `report_url=` lines in `aide.conf` | ✅ JSON |
| `report_format=json` appended to end of `aide.conf` | ❌ Plain text (silent — what tripped the earlier test) |
| `report_url=stdout?report_format=json` (per-URL query string) | ❌ `unknown URL-type` error in 0.18.6 |

AL9 / AL2 remain as before — AIDE 0.16.x has no `report_format` option at all, producing `Configuration error: unknown expression`.

## 🔄 Changes

- 🐛 **aide/README.md** — Rewrote the "About `report_format=json` on Amazon Linux 2023" section with the actual root cause, a four-row results table, and rationale for keeping the Python parser as the recommended pipeline (uniform schema across OSes, JSONL, host enrichment)
- 📝 **README.md** — Updated the Key Findings table; changed section heading from "None of the tested builds have native JSON" to reflect that AL2023 does produce native JSON when configured correctly
- 📝 **CLAUDE.md** — Updated the key findings table to match
- 🆕 **aide/amazonlinux2023/native-json-demo.sh** — Runnable A/B reproducer that demonstrates all four config variations (works via CLI, works via insert, broken via append, errors via per-URL query)
- 🐙 **aide/amazonlinux2023/Dockerfile** — Bakes the demo script into the image at `/usr/local/bin/native-json-demo.sh`
- 🤖 **.github/workflows/ci.yml** — New `verify-aide-native-json-al2023` job that (a) parses `aide --check -B 'report_format=json'` through `json.loads` to prove it's valid JSON, and (b) runs the demo script end-to-end

## ✅ Verification

```bash
# Build the AL2023 image and prove native JSON works
docker build -t amazonlinux2023-aide:latest -f aide/amazonlinux2023/Dockerfile .

# Parse native JSON output
docker run --rm amazonlinux2023-aide:latest bash -c '
  echo tampered >> /etc/passwd
  aide --check -B "report_format=json" 2>/dev/null | python3 -m json.tool
' | head -15

# Run the A/B reproducer — shows all four cases side by side
docker run --rm amazonlinux2023-aide:latest bash /usr/local/bin/native-json-demo.sh
```

Demo script output on AL2023 / AIDE 0.18.6:

```
=== CLI: aide --check -B 'report_format=json' (expected: JSON) ===
{
=== Config: report_format=json APPENDED to aide.conf (expected: plain text — broken) ===
Start timestamp: 2026-04-22 15:24:54 +0000 (AIDE 0.18.6)
=== Config: report_format=json INSERTED before report_url= (expected: JSON) ===
{
=== Config: report_url=stdout?report_format=json (expected: unknown URL-type error) ===
  ERROR: /etc/aide.conf:223: unknown URL-type: 'stdout?report_format=json'
```

Existing smoke tests (Python parser path on all three OSes) still pass locally.

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)

---

## PR #3 — 📝 docs: add AIDE native JSON vs wrapper comparison, fix shell script line endings

**Merged:** 2026-04-23T10:58:10Z · **Commit:** `a6159a25ec`

## 📝 Summary

Adds a detailed comparison document analyzing AIDE's native `report_format=json` output vs the Python wrapper on Amazon Linux 2023, and fixes CRLF line endings on shell scripts so they run in Docker from any host OS.

## 🔄 Changes

- 📄 **`aide/amazonlinux2023/native-json-comparison.md`** — New comparison doc with side-by-side schema analysis, output samples, and recommendation (keep Python wrapper as default for SIEM cross-OS uniformity)
- 🔧 **`.gitattributes`** — New file enforcing `eol=lf` on `*.sh` so shell scripts work inside Linux containers regardless of whether the host is Windows/Mac/Linux
- 🔧 **`aide/amazonlinux2023/native-json-demo.sh`** — Normalized from CRLF to LF
- 📝 **`README.md`** — Added link to comparison doc in the Key Findings section
- 📝 **`aide/README.md`** — Added link to comparison doc alongside the existing demo script reference
- 📝 **`CLAUDE.md`** — Added `.gitattributes` note to Cross-Platform Notes

## ✅ Verification

```bash
# Build and verify the demo script runs without line-ending errors
docker build -t amazonlinux2023-aide:latest -f aide/amazonlinux2023/Dockerfile .
docker run --rm amazonlinux2023-aide:latest bash -c "bash /usr/local/bin/native-json-demo.sh"

# Verify line endings
file aide/amazonlinux2023/native-json-demo.sh
# Expected: "...with LF line terminators" (no CRLF)
```

CI will also validate via `.github/workflows/ci.yml` (builds all 6 images + smoke tests).

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)

---

## PR #4 — ✅ test: add repeatable test script and sample results for all scanner/OS combos

**Merged:** 2026-04-23T11:40:45Z · **Commit:** `1a5af8dd65`

## 📝 Summary

Adds a repeatable test runner script (`scripts/run-tests.sh`) and sample result files for all 6 scanner/OS combinations, replacing the previously empty/incomplete results directories with complete reference outputs.

## 🔄 Changes

- ✅ **New test runner** — `scripts/run-tests.sh` builds images, runs scans, and saves results to `*/results/` directories. Supports `--build-only`, `--scanner`, and `--os` filters.
- ✅ **Sample results for all 6 combos** — ClamAV (almalinux9, amazonlinux2, amazonlinux2023) and AIDE (almalinux9, amazonlinux2, amazonlinux2023) now each have `*.log` (raw output) and `*.json` (parser output) reference files.
- ✅ **Renamed result extensions** — `.txt` → `.log` for raw scanner output, `.txt` → `.json` for parser output, matching content type.
- 🔧 **Updated `.gitignore`** — Changed from blanket `*/results/` to only ignore runtime `*.log` and `*.jsonl`, allowing sample result files to be tracked.
- 📝 **Updated docs** — `README.md`, `CLAUDE.md`, `clamav/README.md`, and `aide/README.md` now document the results directories, file naming, and test script usage.
- 🗑️ **Removed stale files** — Deleted old `clamscan-comparison.txt` and `clamscan-json.txt` (showed engine 1.4.3 for AL9, which was from before the ClamAV upgrade).

## ✅ Verification

```bash
# Run the test script to verify results regenerate correctly
./scripts/run-tests.sh

# Or build only
./scripts/run-tests.sh --build-only

# Single combo
./scripts/run-tests.sh --scanner aide --os almalinux9

# Verify result files exist for all combos
find . -path '*/results/*' -type f | sort
```

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)

---

## PR #5 — 👷 ci: upload sample scan results as downloadable artifacts

**Merged:** 2026-04-23T11:59:44Z · **Commit:** `fea36ffb90`

## 📝 Summary

Adds artifact upload steps to CI so every workflow run publishes sample scanner output (`.log` + `.json`) as downloadable artifacts.

## 🔄 Changes

- 👷 **ClamAV jobs** — After smoke tests, generate `clamscan.log` and `clamscan.json` and upload as `clamav-<os>-results` artifact
- 👷 **AIDE jobs** — After smoke tests, generate `aide.log` and `aide.json` (clean + tampered) and upload as `aide-<os>-results` artifact
- 📝 **Updated root README** — Document artifact availability in the CI section
- ⏱️ **30-day retention** on all artifacts

## ✅ Verification

```bash
# Push triggers CI — check the workflow run for 6 artifact uploads:
#   clamav-almalinux9-results
#   clamav-amazonlinux2-results
#   clamav-amazonlinux2023-results
#   aide-almalinux9-results
#   aide-amazonlinux2-results
#   aide-amazonlinux2023-results
```

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)

---

## PR #6 — ✨ feat: achieve feature parity between AIDE parser and native JSON output

**Merged:** 2026-04-23T13:14:57Z · **Commit:** `f68a02b841`

## 📝 Summary

Adds 5 new parsing capabilities to `aide-to-json.py` so the Python wrapper achieves full feature parity with AIDE 0.18.6's native `report_format=json` output, plus updates all documentation and sample results to reflect the new fields.

## 🔄 Changes

- **`aide/shared/aide-to-json.py`** — 5 new capabilities:
  - `outline` — captures AIDE's status message (e.g. "AIDE found differences between database and filesystem!!")
  - `run_time_seconds` — parses scan duration from the end timestamp line
  - `added_entries` — fixed regex to capture `f++++++++++++++++` format, now lists added files with flag strings
  - `changed_entries` — fixed regex to capture `f > ... mc..H..` format with flag strings (replaces old `changed_attrs`/`attributes` fields with unified `flags` key)
  - `databases` — parses the full database hash section including multi-line values (MD5, SHA256, SHA512, WHIRLPOOL, GOST, STRIBOG256, STRIBOG512, etc.)
- **`aide/amazonlinux2023/native-json-comparison.md`** — updated to reflect feature parity; added parity table showing all fields now match
- **`aide/README.md`** — new JSON schema examples with all fields, field reference table, and new jq examples (added files, flag strings, database hashes, scan duration tracking)
- **`CLAUDE.md`** — added AIDE JSON Output Fields section for AI context accuracy
- **`aide/*/results/aide.json`** (all 3 OSes) — regenerated from docker runs with new parser output including `outline`, `run_time_seconds`, `added_entries`, `changed_entries`, and `databases`

## ✅ Verification

- Built all 3 AIDE Docker images and ran scans on AlmaLinux 9, Amazon Linux 2, and Amazon Linux 2023
- All 3 OSes produce `outline`, `run_time_seconds`, `added_entries`, `changed_entries`, and `databases` fields
- Compact JSON lines in sample results validated as valid JSON
- CI workflow and validation scripts are backward-compatible (new fields are additive)

## 🔗 Sources

- Continuation of work from PRs #3, #4, #5 (AIDE parser improvements)

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)

---

## PR #7 — 🐛 fix: portable run-tests.sh quoting + native ARM64 ClamAV support

**Merged:** 2026-04-23T14:11:47Z · **Commit:** `0dc14ae04d`

## 📝 Summary

Two related portability fixes so the test rig works natively on both Intel x86_64 and Apple Silicon / ARM hosts.

## 🔍 Bug 1 — `scripts/run-tests.sh` unclosed quote aborts silently

Both `echo \"Image: '\"\$TAG\"'` lines (in the clamav + aide test blocks) were missing the closing `\"`. Under `set -euo pipefail` the inner `bash -c` hits `unexpected EOF while looking for matching \"` and the whole script exits before producing the `.log` files.

The failure was invisible because `*/results/*.log` is gitignored — the `.json` blocks run as separate `docker run` invocations with no `\$TAG` splice, so those succeeded and the committed results looked plausible.

**Fix:** pass `TAG` into the container via `docker run -e TAG=...` and reference plain `\$TAG` inside the single-quoted `bash -c`. Fewer quoting layers; behaves identically on macOS zsh, Linux bash, and Git Bash on Windows.

## 🔍 Bug 2 — Cisco ClamAV Dockerfiles pinned to x86_64

`clamav/almalinux9/Dockerfile` and `clamav/amazonlinux2023/Dockerfile` hardcoded `clamav-1.5.2.linux.x86_64.rpm`, so builds on ARM hosts failed with:

```
package clamav-1.5.2-1.x86_64 from @commandline does not have a compatible architecture
```

Cisco publishes both `x86_64` and `aarch64` RPMs for 1.5.2. The Dockerfiles now read `ARG TARGETARCH` (set automatically by Docker buildx) and select the matching RPM + pinned SHA256. Falls back to `amd64` if `TARGETARCH` is unset (plain `docker build` without buildx).

Amazon Linux 2 ClamAV is unaffected — it installs from EPEL, which already has arm64 builds.

## 🔄 Changes

- 🐛 **scripts/run-tests.sh** — replace fragile `'\"\$TAG\"'` splice with `docker run -e TAG=...` env-var injection in both the clamav and aide test blocks
- 🐙 **clamav/almalinux9/Dockerfile** — add `ARG TARGETARCH` + case-select between `x86_64` / `aarch64` RPM and its SHA256
- 🐙 **clamav/amazonlinux2023/Dockerfile** — same arch-aware RPM selection
- 📊 ***/results/*.json** — regenerated from the repaired script across all 6 scanner/OS combos. Previous versions included a pretty-printed appendix that no current script path produces; the files are now just the single-line JSONL output the `-to-json.py` parsers actually emit, with a header banner comment per block

## ✅ Verification

Full test run on `darwin/arm64` (Apple Silicon, Docker Desktop):

```bash
# All 6 images build natively
./scripts/run-tests.sh --build-only

# Full scan + result generation
./scripts/run-tests.sh
```

All 6 combos produce valid single-line JSONL that parses cleanly:

```bash
$ for f in aide/*/results/aide.json clamav/*/results/clamscan.json; do
    grep -vE '^(===|\$)' \"\$f\" | while read -r line; do
      echo \"\$line\" | python3 -c 'import sys,json; json.loads(sys.stdin.read())' && echo \"  OK: \$f\"
    done
  done
  # 12 lines, all parsed OK
```

Native-JSON A/B reproducer still prints the four expected outcomes on AL2023:

```bash
docker run --rm amazonlinux2023-aide:latest bash /usr/local/bin/native-json-demo.sh
# === CLI: aide --check -B 'report_format=json' (expected: JSON)                  → {
# === Config: report_format=json APPENDED to aide.conf (expected: plain — broken) → Start timestamp:
# === Config: report_format=json INSERTED before report_url= (expected: JSON)     → {
# === Config: report_url=stdout?report_format=json (expected: unknown URL-type)   → ERROR
```

CI (ubuntu-latest / amd64) is unaffected — the Dockerfile change is a no-op on amd64 since the fallback branch selects the same RPM it always used.

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)

---

## PR #9 — 🐛 fix: parse multi-line ACL values correctly in aide-to-json.py (#8)

**Merged:** 2026-04-23T14:29:04Z · **Commit:** `49b1fc3c41`

Closes #8.

## 📝 Summary

`aide-to-json.py` was mangling multi-line ACL entries, producing spurious `detailed_changes` entries with `"attribute":"A"` and losing two of the three ACL permission rows. This PR fixes the parser, adds a stdlib-only unit test, and wires it into CI.

## 🔍 Root cause

AIDE wraps long attribute values across multiple indented lines:

```
 ACL       : A: user::rw-                     | A: user::rwx
             A: group::r--                    | A: group::rwx
             A: other::r--                    | A: other::rwx
```

The parser's attribute-line regex `^(\w+)\s*:\s+(.+)$` matches continuation lines too — because `A:` looks like a valid attribute introducer. So instead of extending the existing ACL entry, the parser minted fresh `{"attribute":"A"}` entries and leaked the continuation prefix `A: ` into the `new` field. The previous multi-line-hash continuation branch never ran.

## 🔄 Changes

- 🐛 **aide/shared/aide-to-json.py** — Distinguish attribute-introducing lines from continuation lines using indentation: AIDE uses 1–2 leading spaces for attributes, ~13 for continuations. Lines with 8+ leading spaces are now treated as continuations of the current attribute. Added a `_MULTIVALUE_ATTRS = {"ACL", "XAttrs"}` set so list-style values join with spaces between rows (hashes keep concatenating without separators).
- 🐛 **aide/shared/aide-to-json.py** — Broadened the sidecar-log exception handler from `PermissionError` to `OSError` so the parser doesn't crash on `FileNotFoundError` when `/var/log/aide/` doesn't exist (e.g. during unit tests). The JSONL sidecar is best-effort; stdout is the primary sink.
- 🆕 **scripts/test-aide-parser.py** — New stdlib-only unit test (no Docker needed). Covers: ACL multi-line regression (#8), 3-line SHA512 continuation concatenation, attribute ordering, absence of bogus `"A"` entries, and basic outline/summary/run_time fields.
- 🤖 **.github/workflows/ci.yml** — New `aide-parser-unit-tests` job on `ubuntu-latest` that runs the parser tests without building any Docker images. Fast feedback before the matrix jobs start.
- 📊 **aide/*/results/aide.json** — Regenerated across all three OSes. Each file now contains a single consolidated ACL entry per path (three permission rows joined with spaces) and zero bogus `"attribute":"A"` entries.

## ✅ Verification

Unit test (runs on any host, no Docker):

```bash
$ python3 scripts/test-aide-parser.py
PASS: all parser assertions hold
  detailed_changes attrs: ['Size', 'Perm', 'SHA256', 'SHA512', 'ACL']
  ACL.old = A: user::rw- A: group::r-- A: other::r--
  ACL.new = A: user::rwx A: group::rwx A: other::rwx
```

End-to-end on all three AIDE versions (0.16 / 0.16.2 / 0.18.6):

```bash
$ for img in almalinux9-aide amazonlinux2-aide amazonlinux2023-aide; do
    docker run --rm $img:latest bash -c '
      chmod 777 /etc/resolv.conf
      aide -C 2>&1 | python3 /usr/local/bin/aide-to-json.py
    ' | python3 -c 'import sys,json; d=json.loads(sys.stdin.read());
      print(img, "ACL=", [c for c in d["detailed_changes"] if c["attribute"]=="ACL"],
            "bogus A=", [c for c in d["detailed_changes"] if c["attribute"]=="A"])'
  done
# Every OS: exactly 1 ACL entry per changed path, 0 bogus A entries
```

## 🔁 Backwards compatibility

- Hash attributes (SHA256/SHA512/etc.) still concatenate without separators — the space-join only applies to `ACL` and `XAttrs`. Fixture test covers a 3-line SHA512 to guard against regression.
- Single-line attributes (Size, Perm, Inode, …) unchanged.
- Existing JSONL consumers parsing `detailed_changes[].attribute` and `.old`/`.new` continue to work. The change is that previously malformed entries stop appearing.

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)

---

## PR #11 — ✨ feat: add automated test results report generator

**Merged:** 2026-04-24T11:43:23Z · **Commit:** `7a94d32dc4`

## Summary

Add `scripts/generate-report.sh` — a pure bash/sed script that parses test result files (`.log` and `.json`) from all scanner/OS combos and produces a detailed `TEST-RESULTS-BREAKDOWN.md` report. No LLM needed; fully repeatable from raw result files.

## Changes

- ✨ **New: `scripts/generate-report.sh`** (~630 lines) — Parses ClamAV and AIDE result files across all 3 OSes, extracting version numbers, scan timings, entry counts, changed file lists, hash algorithms, and file sizes. Produces a structured markdown report with:
  - Per-OS breakdown tables for ClamAV and AIDE
  - Cross-OS comparison tables with metrics and hash algorithm matrices
  - JSONL append validation section
  - Full file inventory with sizes
  - Static explanatory prose (Docker artifact notes, version differences)
- 🔧 **Updated: `scripts/run-tests.sh`** — Calls `generate-report.sh` at the end of the test run so the report is always up-to-date after builds
- 📝 **Updated: `README.md`** — Added `generate-report.sh` and `TEST-RESULTS-BREAKDOWN.md` to project structure, added "Test Results Report" section
- 📝 **Updated: `CLAUDE.md`** — Added script to project structure and build commands

## Verification

```bash
# Generate report from existing results (no Docker needed):
./scripts/generate-report.sh

# Verify the report was created:
head -10 TEST-RESULTS-BREAKDOWN.md

# Full pipeline (build + test + report):
./scripts/run-tests.sh
```

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)

---

## PR #12 — 📝 docs: add PR #11 to HISTORY.md

**Merged:** 2026-04-24T18:50:41Z · **Commit:** `a93c0d1005`

## 📝 Summary

Appends PR #11 (the test-results report generator, commit `7a94d32`) to `HISTORY.md` so the mirror on git.soma continues to carry the full rationale for every merged PR.

## 🔄 Changes

- 📝 **HISTORY.md** — one new section for PR #11 with merge date, commit SHA, and transcribed PR body; timeline table row added.

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)

---

## PR #13 — 📝 docs: add Zread CLI wiki and documentation references

**Merged:** 2026-04-25T09:56:58Z · **Commit:** `c6f11551a7`

## Summary

Add the AI-generated Zread CLI project wiki (`.zread/`) to the repository and update project documentation with references and maintenance guidance.

## Changes

- 📄 **`.zread/wiki/`** — 22-topic AI-generated wiki covering architecture, parsers, Dockerfiles, CI, SIEM integration, and more (generated via `zread generate`)
- 📝 **`CLAUDE.md`** — Added `.zread/` to project structure tree and new "Zread Wiki" section with update workflow and prune-before-commit guidance
- 📝 **`README.md`** — Added `.zread/wiki/` link to the Detailed Documentation section
- 🔧 **`.gitignore`** — Added `.claude/` and `.zread/wiki/drafts/` (in-progress generation artifacts)

## Verification

```bash
# Verify wiki content is present
ls .zread/wiki/versions/*/  # Should show 22 .md files + wiki.json

# Verify gitignore excludes drafts
cat .gitignore | grep zread  # Should show .zread/wiki/drafts/

# Verify docs references
grep -n zread README.md CLAUDE.md
```

---

🤖 Generated with [Claude Code](https://claude.com/claude-code)

---

## Issue #8 — 🐛 aide-to-json.py misparses multi-line ACL continuations

**State:** CLOSED · **Closed:** 2026-04-23T14:29:05Z · **Reason:** COMPLETED

## Summary

`aide/shared/aide-to-json.py` creates spurious `detailed_changes` entries for ACL attributes whose values span multiple lines. The issue is visible in any tampered scan on AL2023 where `/etc/resolv.conf` has its permissions changed (which produces an ACL diff).

## Reproduction

```bash
docker build -t amazonlinux2023-aide:latest -f aide/amazonlinux2023/Dockerfile .
docker run --rm amazonlinux2023-aide:latest bash -c '
  chmod 777 /etc/resolv.conf
  aide -C 2>&1 | python3 /usr/local/bin/aide-to-json.py | python3 -m json.tool | grep -A4 -E "\"ACL\"|\"attribute\": \"A\""
'
```

## Expected vs actual

Raw AIDE output for a multi-line ACL attribute:

```
 ACL       : A: user::rw-                     | A: user::rwx
             A: group::r--                    | A: group::rwx
             A: other::r--                    | A: other::rwx
```

**Expected (one logical entry per attribute):**
```json
{
  "path": "/etc/resolv.conf",
  "attribute": "ACL",
  "old": "A: user::rw- A: group::r-- A: other::r--",
  "new": "A: user::rwx A: group::rwx A: other::rwx"
}
```

**Actual (three bogus entries after the real one):**
```json
{"path":"/etc/resolv.conf","attribute":"ACL","old":"A: user::rw-","new":"A: user::rwx"},
{"path":"/etc/resolv.conf","attribute":"A","old":"group::r--","new":"A: group::rwx"},
{"path":"/etc/resolv.conf","attribute":"A","old":"other::r--","new":"A: other::rwx"}
```

The attribute name collapses to `"A"` and the `new` value leaks the continuation prefix `A: `.

## Root cause

Two regexes in `parse_aide()` both match ACL continuation lines:

1. The attribute-line regex at `aide/shared/aide-to-json.py:117` — `^(\w+)\s*:\s+(.+)\$` — matches `A: group::r-- | A: group::rwx` because `A` looks like an attribute name.
2. The multi-line hash continuation branch at `:134-143` never gets a chance.

The attribute regex fires first and creates a new `detailed_changes` entry.

## Fix direction

Continuation lines are indented; attribute-introducing lines are not. Check the raw `line` (not `s = line.strip()`) for leading whitespace before treating it as a new attribute — if it's indented and a prior attribute is in-flight, treat it as continuation.

A narrower alternative: whitelist the attribute-regex to the known AIDE attribute vocabulary (`Size|Mtime|Ctime|Inode|SHA\\d+|...|ACL|XAttrs`) so single-letter values like `A:` don't hijack the match.

## Impact

- Affects any attribute whose value itself contains `word:` syntax on continuation lines (ACL is the confirmed case; SELinux labels / XAttrs are plausible candidates).
- The `old`/`new` values lose their line breaks, which distorts jq queries against those attributes.
- The extra `"attribute":"A"` entries pollute the `detailed_changes` array and are easy to mistake for real file-attribute deltas in dashboards.

## Scope

Not fixing in PR #7 since that one is scoped to portability. Worth a separate PR with a unit test covering multi-line ACL + multi-line hash (which currently works) in the same fixture.

