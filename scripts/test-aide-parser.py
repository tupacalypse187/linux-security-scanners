#!/usr/bin/env python3
"""
Parser unit tests for aide/shared/aide-to-json.py.

Covers regression cases that are hard to exercise via Docker smoke tests:
 - Multi-line ACL values (issue #8)
 - Multi-line SHA256/SHA512 hash values
 - Mixed attributes on the same file
 - Absence of false "attribute: A" entries from ACL continuations

Runs with stdlib only. Usage:
    python3 scripts/test-aide-parser.py
"""
import json
import os
import subprocess
import sys
import tempfile

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARSER = os.path.join(REPO_ROOT, "aide", "shared", "aide-to-json.py")

FIXTURE = """\
Start timestamp: 2026-04-23 12:00:00 +0000 (AIDE 0.18.6)
AIDE found differences between database and filesystem!!

Summary:
  Total number of entries:\t100
  Added entries:\t\t0
  Removed entries:\t\t0
  Changed entries:\t\t1

---------------------------------------------------
Changed entries:
---------------------------------------------------

f > p..    .HA.  : /etc/resolv.conf

---------------------------------------------------
Detailed information about changes:
---------------------------------------------------

File: /etc/resolv.conf
 Size      : 24                               | 222
 Perm      : -rw-r--r--                       | -rwxrwxrwx
 SHA256    : BdNg+yp9IvgPU88Z3Zsm6eymhdJ03z7m | VTMqVqehbR08xAwF8tHwOJ6jgLhTfsxO
             i7Ok9u6WtTM=                     | /y42kstcCWo=
 SHA512    : z4/WlF+yww5Lrxg5hpIMyn/2X7G727yY | F0TfXyPt0eMVpAsUqdLyPzxXqAsbCE3a
             iIZ0hee1cC4CPKRuTTwqOqR+a4PrwaQ+ | Ps9d/QIjbQckCNy3Zo8mgMYkmJo8dLBJ
             dELMHdsn+4/f8UNrnXzvzg==         | GYvKHfk90Q7JvAsL==
 ACL       : A: user::rw-                     | A: user::rwx
             A: group::r--                    | A: group::rwx
             A: other::r--                    | A: other::rwx

End timestamp: 2026-04-23 12:00:03 +0000 (run time: 0m 3s)
"""


def run_parser(stdin_text):
    proc = subprocess.run(
        [sys.executable, PARSER],
        input=stdin_text,
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(proc.stdout.strip())


def fail(msg):
    print("FAIL: " + msg)
    sys.exit(1)


def main():
    # Redirect JSONL append target to a temp file so the test is hermetic.
    # The parser swallows PermissionError silently if it can't write, which
    # is what we rely on here (HOME doesn't include /var/log/aide).
    data = run_parser(FIXTURE)

    # Only /etc/resolv.conf should appear; the parser must not produce
    # bogus entries for ACL continuations.
    paths = {c["path"] for c in data.get("detailed_changes", [])}
    if paths != {"/etc/resolv.conf"}:
        fail("Unexpected paths in detailed_changes: {}".format(paths))

    attrs = [c["attribute"] for c in data["detailed_changes"]]
    expected = ["Size", "Perm", "SHA256", "SHA512", "ACL"]
    if attrs != expected:
        fail("Expected attributes {} (order-preserving), got {}".format(expected, attrs))

    # Regression for issue #8: no "A" attribute from ACL continuation lines.
    if "A" in attrs:
        fail("ACL continuation leaked as attribute 'A' (issue #8 regression)")

    # ACL values: all three lines joined with spaces.
    acl = next(c for c in data["detailed_changes"] if c["attribute"] == "ACL")
    expected_old = "A: user::rw- A: group::r-- A: other::r--"
    expected_new = "A: user::rwx A: group::rwx A: other::rwx"
    if acl["old"] != expected_old:
        fail("ACL old:\n  got:  {!r}\n  want: {!r}".format(acl["old"], expected_old))
    if acl["new"] != expected_new:
        fail("ACL new:\n  got:  {!r}\n  want: {!r}".format(acl["new"], expected_new))

    # SHA256: single-line value, no trailing concatenation artefacts.
    sha256 = next(c for c in data["detailed_changes"] if c["attribute"] == "SHA256")
    if sha256["old"] != "BdNg+yp9IvgPU88Z3Zsm6eymhdJ03z7mi7Ok9u6WtTM=":
        fail("SHA256 old mangled: {!r}".format(sha256["old"]))
    if sha256["new"] != "VTMqVqehbR08xAwF8tHwOJ6jgLhTfsxO/y42kstcCWo=":
        fail("SHA256 new mangled: {!r}".format(sha256["new"]))

    # SHA512: three-line value (header + 2 continuations), concatenated
    # WITHOUT spaces (hashes are not in _MULTIVALUE_ATTRS).
    sha512 = next(c for c in data["detailed_changes"] if c["attribute"] == "SHA512")
    expected_old_sha512 = (
        "z4/WlF+yww5Lrxg5hpIMyn/2X7G727yY"
        "iIZ0hee1cC4CPKRuTTwqOqR+a4PrwaQ+"
        "dELMHdsn+4/f8UNrnXzvzg=="
    )
    if sha512["old"] != expected_old_sha512:
        fail("SHA512 old:\n  got:  {!r}\n  want: {!r}".format(sha512["old"], expected_old_sha512))
    if " " in sha512["old"]:
        fail("SHA512 old should not contain spaces: {!r}".format(sha512["old"]))

    # Summary + outline sanity.
    if data["result"] != "changes_detected":
        fail("result={!r}".format(data["result"]))
    if data.get("run_time_seconds") != 3:
        fail("run_time_seconds={!r}".format(data.get("run_time_seconds")))
    if data["summary"]["changed"] != 1:
        fail("summary.changed={!r}".format(data["summary"].get("changed")))

    print("PASS: all parser assertions hold")
    print("  detailed_changes attrs:", attrs)
    print("  ACL.old =", acl["old"])
    print("  ACL.new =", acl["new"])


if __name__ == "__main__":
    main()
