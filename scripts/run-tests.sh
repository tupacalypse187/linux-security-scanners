#!/usr/bin/env bash
# run-tests.sh — Build all images, run scans, and save sample results
# Usage: ./scripts/run-tests.sh [--build-only] [--scanner clamav|aide] [--os almalinux9|amazonlinux2|amazonlinux2023]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

SCANNERS=("clamav" "aide")
OSES=("almalinux9" "amazonlinux2" "amazonlinux2023")
BUILD_ONLY=0

# Parse arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    --build-only) BUILD_ONLY=1; shift ;;
    --scanner)
      SCANNERS=("$2"); shift 2 ;;
    --os)
      OSES=("$2"); shift 2 ;;
    -h|--help)
      echo "Usage: $0 [--build-only] [--scanner clamav|aide] [--os almalinux9|amazonlinux2|amazonlinux2023]"
      echo ""
      echo "Build all Docker images and run scans to populate */results/ directories."
      echo ""
      echo "Options:"
      echo "  --build-only    Build images only, skip scan tests"
      echo "  --scanner       Run only the specified scanner"
      echo "  --os            Run only on the specified OS"
      exit 0 ;;
    *)
      echo "Unknown option: $1" >&2; exit 1 ;;
  esac
done

echo "=========================================="
echo "Linux Security Scanners — Test Runner"
echo "=========================================="
echo ""

# --- Build ---
for scanner in "${SCANNERS[@]}"; do
  for os in "${OSES[@]}"; do
    TAG="${os}-${scanner}:latest"
    DOCKERFILE="${scanner}/${os}/Dockerfile"

    if [[ ! -f "$DOCKERFILE" ]]; then
      echo "SKIP: $DOCKERFILE not found"
      continue
    fi

    echo "BUILD: $TAG"
    docker build -t "$TAG" -f "$DOCKERFILE" . 2>&1 | tail -3
    echo ""
  done
done

if [[ $BUILD_ONLY -eq 1 ]]; then
  echo "Build-only mode. Done."
  exit 0
fi

# --- ClamAV Tests ---
for os in "${OSES[@]}"; do
  TAG="${os}-clamav:latest"
  RESULT_DIR="clamav/${os}/results"

  if ! docker image inspect "$TAG" >/dev/null 2>&1; then
    echo "SKIP: $TAG not built"
    continue
  fi

  echo "=========================================="
  echo "TEST: ClamAV — $os"
  echo "=========================================="

  mkdir -p "$RESULT_DIR"

  # Raw comparison (with/without summary). Pass TAG via `-e` so the
  # container-side script can reference it without fragile host-side
  # single-quote gymnastics.
  docker run --rm -e TAG="$TAG" "$TAG" bash -c '
    echo "========================================"
    echo "clamscan WITH summary (default)"
    echo "Command: clamscan /etc/hostname /etc/hosts /etc/passwd /etc/resolv.conf"
    echo "Image: $TAG"
    echo "Date: $(date -u +%Y-%m-%d)"
    echo "========================================"
    echo ""
    clamscan /etc/hostname /etc/hosts /etc/passwd /etc/resolv.conf
    echo ""
    echo "========================================"
    echo "clamscan WITHOUT summary (--no-summary)"
    echo "Command: clamscan --no-summary /etc/hostname /etc/hosts /etc/passwd /etc/resolv.conf"
    echo "========================================"
    echo ""
    clamscan --no-summary /etc/hostname /etc/hosts /etc/passwd /etc/resolv.conf
  ' > "${RESULT_DIR}/clamscan.log"

  echo "  -> ${RESULT_DIR}/clamscan.log"

  # JSON comparison
  docker run --rm "$TAG" bash -c '
    mkdir -p /var/log/clamav
    echo "=== WITH summary (1 JSON line) ==="
    clamscan /etc/hostname /etc/hosts /etc/passwd /etc/resolv.conf | python3 /usr/local/bin/clamscan-to-json.py
    echo ""
    echo "=== WITHOUT summary --no-summary (1 JSON line) ==="
    clamscan --no-summary /etc/hostname /etc/hosts /etc/passwd /etc/resolv.conf | python3 /usr/local/bin/clamscan-to-json.py
  ' > "${RESULT_DIR}/clamscan.json"

  echo "  -> ${RESULT_DIR}/clamscan.json"
  echo ""
done

# --- AIDE Tests ---
for os in "${OSES[@]}"; do
  TAG="${os}-aide:latest"
  RESULT_DIR="aide/${os}/results"

  if ! docker image inspect "$TAG" >/dev/null 2>&1; then
    echo "SKIP: $TAG not built"
    continue
  fi

  echo "=========================================="
  echo "TEST: AIDE — $os"
  echo "=========================================="

  mkdir -p "$RESULT_DIR"

  # Raw check output. Pass TAG via `-e` so the inner script can reference
  # it without fragile host-side single-quote gymnastics.
  docker run --rm -e TAG="$TAG" "$TAG" bash -c '
    echo "========================================"
    echo "AIDE clean check — $(aide --version 2>&1 | head -1)"
    echo "Image: $TAG"
    echo "Date: $(date -u +%Y-%m-%d)"
    echo "========================================"
    echo ""
    echo "NOTE: Docker containers generate baseline changes (hostname, resolv.conf, package"
    echo "installation artifacts) because the AIDE database is initialized at image build time."
    echo "This is expected behavior."
    echo ""
    echo "=== CLEAN CHECK (no tampering) ==="
    aide -C 2>&1
    echo ""
    echo "=== CHECK WITH TAMPERED FILE ==="
    echo "(Echo \"tampered\" to /tmp/ci-test-hack, chmod 777 /etc/resolv.conf)"
    echo "tampered" > /tmp/ci-test-hack
    chmod 777 /etc/resolv.conf
    aide -C 2>&1 | head -80
  ' > "${RESULT_DIR}/aide.log"

  echo "  -> ${RESULT_DIR}/aide.log"

  # JSON check output
  docker run --rm "$TAG" bash -c '
    mkdir -p /var/log/aide
    echo "=== CLEAN CHECK (1 JSON line) ==="
    aide -C 2>&1 | python3 /usr/local/bin/aide-to-json.py
    echo ""
    echo "=== TAMPERED CHECK (1 JSON line) ==="
    echo "tampered" > /tmp/ci-test-hack
    chmod 777 /etc/resolv.conf
    aide -C 2>&1 | python3 /usr/local/bin/aide-to-json.py
  ' > "${RESULT_DIR}/aide.json"

  echo "  -> ${RESULT_DIR}/aide.json"
  echo ""
done

echo "=========================================="
echo "Done! Results saved to */results/ directories."
echo "=========================================="

# --- Generate Report ---
echo ""
echo "Generating TEST-RESULTS-BREAKDOWN.md..."
bash "$SCRIPT_DIR/generate-report.sh"
echo ""
