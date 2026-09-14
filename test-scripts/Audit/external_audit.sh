#!/usr/bin/env bash
set -euo pipefail

# --- TARGET VALIDATION ---
TARGET_IP="${1:-YOUR_VPS_PUBLIC_IP}"
if [[ "${TARGET_IP}" == "YOUR_VPS_PUBLIC_IP" || -z "${TARGET_IP}" ]]; then
  echo "[-] Error: Please supply a target IP or set TARGET_IP."
  echo "[-] Usage: $0 <TARGET_IP>"
  exit 1
fi

DOMAINS=(
  "humid1.com"
  "app.humid1.com"
  "auth.humid1.com"
  "bw.humid1.com"
  "cap.humid1.com"
  "chat.humid1.com"
  "dash.humid1.com"
)

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BASE_DIR="$(pwd)"
REPORT_DIR="${BASE_DIR}/external_security_audit_${TIMESTAMP}"
mkdir -p "${REPORT_DIR}/nmap" "${REPORT_DIR}/ssl" "${REPORT_DIR}/zap"

# Ensure ZAP container (UID 1000) has write access to the report volume
chmod 777 "${REPORT_DIR}/zap"

echo "=================================================="
echo " [1/3] EXTERNAL PERIMETER SCAN (NMAP) "
echo "=================================================="
echo "[-] Probing open ports on ${TARGET_IP}..."
docker run --rm \
  -v "${REPORT_DIR}/nmap:/out" \
  instrumentasto/nmap \
  -sV -F -oN "/out/nmap_fast_scan.txt" "${TARGET_IP}" || true

echo "=================================================="
echo " [2/3] SSL/TLS CONFIGURATION SCAN (TESTSSL.SH) "
echo "=================================================="
for domain in "${DOMAINS[@]}"; do
  echo "[-] Testing SSL/TLS for https://${domain}..."
  clean_name=$(echo "${domain}" | tr '.' '_')
  docker run --rm \
    -v "${REPORT_DIR}/ssl:/out" \
    drwetter/testssl.sh \
    --severity HIGH \
    --jsonfile "/out/${clean_name}_ssl.json" \
    "https://${domain}" || true
done

echo "=================================================="
echo " [3/3] WEB APPLICATION BASELINE SCAN (OWASP ZAP) "
echo "=================================================="
for domain in "${DOMAINS[@]}"; do
  clean_name=$(echo "${domain}" | tr '.' '_')
  echo "[-] Running ZAP Baseline on https://${domain}..."
  
  docker run --rm \
    -v "${REPORT_DIR}/zap:/zap/wrk/:rw" \
    zaproxy/zap-stable \
    zap-baseline.py \
    -t "https://${domain}" \
    -r "${clean_name}_zap.html" \
    -J "${clean_name}_zap.json" \
    -I || true
done

echo ""
echo "=================================================="
echo " Audit Complete. All reports saved to:"
echo " ${REPORT_DIR}"
echo "=================================================="