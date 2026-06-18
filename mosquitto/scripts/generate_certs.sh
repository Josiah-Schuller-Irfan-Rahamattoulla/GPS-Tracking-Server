#!/usr/bin/env bash
# Generate self-signed TLS certificates for Mosquitto (development / single-server deploy).
#
# Validity: default 825 days (~27 months). For lab benches you may use 3650 days (10 years);
# for anything production-facing, use a proper CA (Let's Encrypt, internal PKI) instead.
#
# Usage (from repo root, Git Bash or WSL):
#   ./mosquitto/scripts/generate_certs.sh
#   ./mosquitto/scripts/generate_certs.sh 3650   # optional: custom validity in days
#
# Output:
#   mosquitto/config/certs/ca.crt, ca.key
#   mosquitto/config/certs/server.crt, server.key
#
# Devices need ca.crt to verify the broker on port 8883.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
CERT_DIR="${REPO_ROOT}/mosquitto/config/certs"
VALIDITY_DAYS="${1:-825}"

mkdir -p "${CERT_DIR}"

echo "Generating MQTT TLS certs in ${CERT_DIR} (validity ${VALIDITY_DAYS} days)..."

# 1) Certificate Authority (signs the server cert; devices trust ca.crt only)
openssl req -x509 -newkey rsa:2048 -nodes \
  -keyout "${CERT_DIR}/ca.key" \
  -out "${CERT_DIR}/ca.crt" \
  -days "${VALIDITY_DAYS}" \
  -subj "/CN=GPS-Tracking-MQTT-CA"

# 2) Server key + CSR
openssl req -newkey rsa:2048 -nodes \
  -keyout "${CERT_DIR}/server.key" \
  -out "${CERT_DIR}/server.csr" \
  -subj "/CN=mosquitto"

# 3) Sign server cert with our CA (add SAN for localhost + broker hostname)
cat > "${CERT_DIR}/server.ext" <<EOF
subjectAltName = DNS:localhost,DNS:mosquitto,IP:127.0.0.1
EOF

openssl x509 -req \
  -in "${CERT_DIR}/server.csr" \
  -CA "${CERT_DIR}/ca.crt" \
  -CAkey "${CERT_DIR}/ca.key" \
  -CAcreateserial \
  -out "${CERT_DIR}/server.crt" \
  -days "${VALIDITY_DAYS}" \
  -extfile "${CERT_DIR}/server.ext"

rm -f "${CERT_DIR}/server.csr" "${CERT_DIR}/server.ext" "${CERT_DIR}/ca.srl"

chmod 600 "${CERT_DIR}/ca.key" "${CERT_DIR}/server.key"
chmod 644 "${CERT_DIR}/ca.crt" "${CERT_DIR}/server.crt"

echo "Done."
echo "  CA (provision on devices):  ${CERT_DIR}/ca.crt"
echo "  Server cert/key (Mosquitto): ${CERT_DIR}/server.crt, server.key"
echo "Restart Mosquitto after generating: docker compose restart mosquitto"
