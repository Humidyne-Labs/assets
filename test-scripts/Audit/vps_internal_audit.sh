#!/usr/bin/env bash
set -euo pipefail

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BASE_DIR="$(pwd)"
REPORT_DIR="${BASE_DIR}/vps_internal_audit_${TIMESTAMP}"
mkdir -p "${REPORT_DIR}/trivy" "${REPORT_DIR}/lynis" "${REPORT_DIR}/secrets"

echo "=================================================="
echo " [1/3] DOCKER CONTAINER IMAGE AUDIT (TRIVY) "
echo "=================================================="
mkdir -p ~/.cache/trivy
RUNNING_IMAGES=$(docker ps --format '{{.Image}}' | sort -u)

if [[ -z "${RUNNING_IMAGES}" ]]; then
  echo "[-] No running Docker containers found to scan."
else
  for img in $RUNNING_IMAGES; do
    clean_img=$(echo "${img}" | tr '/:' '_')
    echo "[-] Auditing vulnerabilities in image: ${img}"
    docker run --rm \
      -v /var/run/docker.sock:/var/run/docker.sock \
      -v ~/.cache/trivy:/root/.cache/ \
      -v "${REPORT_DIR}/trivy:/out" \
      aquasec/trivy:latest image \
      --severity HIGH,CRITICAL \
      --format json \
      -o "/out/${clean_img}.json" "${img}" || true
  done
fi

echo "=================================================="
echo " [2/3] SECRETS & CREDENTIAL LEAK SCAN (TRUFFLEHOG) "
echo "=================================================="
echo "[-] Scanning local filesystem and compose files for plain-text secrets..."
docker run --rm \
  -v "${BASE_DIR}:/pwd:ro" \
  trufflesecurity/trufflehog:latest \
  filesystem /pwd --json --no-update > "${REPORT_DIR}/secrets/trufflehog_results.json" 2>&1 || true

echo "=================================================="
echo " [3/3] HOST OS HARDENING AUDIT (LYNIS) "
echo "=================================================="
if command -v lynis &> /dev/null; then
  echo "[-] Running native Lynis system audit..."
  sudo lynis audit system --quick --report-file "${REPORT_DIR}/lynis/lynis-report.dat" || true
else
  echo "[!] Lynis is not installed natively on the host."
  echo "    Install via package manager (e.g., 'sudo apt install lynis') for best host results."
fi

echo ""
echo "=================================================="
echo " Internal Audit Complete. Reports saved to:"
echo " ${REPORT_DIR}"
echo "=================================================="