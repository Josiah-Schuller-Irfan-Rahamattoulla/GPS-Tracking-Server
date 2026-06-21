#!/usr/bin/env bash
# Create Mosquitto TLS certs if missing (CI + first-time local setup).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CERT_DIR="$(cd "${SCRIPT_DIR}/../config/certs" && pwd)"

if [[ -s "${CERT_DIR}/ca.crt" && -s "${CERT_DIR}/server.crt" && -s "${CERT_DIR}/server.key" ]]; then
  echo "MQTT certs already present in ${CERT_DIR}"
  exit 0
fi

if ! command -v openssl >/dev/null 2>&1; then
  echo "openssl not found; install OpenSSL or run generate_certs.sh on a machine with openssl" >&2
  exit 1
fi

echo "MQTT certs missing — generating dev/CI certificates..."
exec "${SCRIPT_DIR}/generate_certs.sh"
