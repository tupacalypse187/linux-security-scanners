#!/usr/bin/env bash
# Demonstrates that AIDE 0.18.6 on Amazon Linux 2023 DOES support
# report_format=json — but the config directive is order-sensitive.
#
# AIDE applies report_format to each report_url at the moment the URL
# is declared. The default /etc/aide.conf declares two report_url= lines
# near the top, so appending report_format=json to the end of the file
# has no effect — the URLs are already bound to the default 'plain' format.
#
# Run this inside the amazonlinux2023-aide image:
#
#   docker build -t amazonlinux2023-aide:latest -f aide/amazonlinux2023/Dockerfile .
#   docker run --rm amazonlinux2023-aide:latest bash /usr/local/bin/native-json-demo.sh
#
# Or ad-hoc in a fresh container:
#
#   docker run --rm -v $(pwd)/aide/amazonlinux2023/native-json-demo.sh:/demo.sh \
#     amazonlinux:2023 bash -c 'dnf install -y aide >/dev/null && bash /demo.sh'

set -eu

echo "=== AIDE version ==="
aide --version | head -1

if [[ ! -f /var/lib/aide/aide.db.gz ]]; then
  aide --init >/dev/null 2>&1
  cp /var/lib/aide/aide.db.new.gz /var/lib/aide/aide.db.gz
fi
echo "tampered" >> /etc/passwd

cp /etc/aide.conf /etc/aide.conf.orig

# first_line: capture full output, then print its first line. Avoids SIGPIPE
# from `aide | head -1` which would trip `set -e`.
first_line() {
  local out
  out=$(aide --check 2>/dev/null || true)
  echo "${out%%$'\n'*}"
}

echo ""
echo "=== CLI: aide --check -B 'report_format=json' (expected: JSON) ==="
out=$(aide --check -B 'report_format=json' 2>/dev/null || true)
echo "${out%%$'\n'*}"

cp /etc/aide.conf.orig /etc/aide.conf
echo 'report_format=json' >> /etc/aide.conf
echo ""
echo "=== Config: report_format=json APPENDED to aide.conf (expected: plain text — broken) ==="
first_line

cp /etc/aide.conf.orig /etc/aide.conf
sed -i '/^report_url=/i report_format=json' /etc/aide.conf
echo ""
echo "=== Config: report_format=json INSERTED before report_url= (expected: JSON) ==="
first_line

cp /etc/aide.conf.orig /etc/aide.conf
sed -i '/^report_url=/d' /etc/aide.conf
echo 'report_url=stdout?report_format=json' >> /etc/aide.conf
echo ""
echo "=== Config: report_url=stdout?report_format=json (expected: unknown URL-type error) ==="
aide --check 2>&1 | head -1 || true

cp /etc/aide.conf.orig /etc/aide.conf
echo ""
echo "=== Done. JSON output begins with '{' — plain text begins with 'Start timestamp:' ==="
