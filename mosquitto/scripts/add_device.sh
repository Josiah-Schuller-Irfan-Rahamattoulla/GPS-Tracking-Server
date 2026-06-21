#!/usr/bin/env bash
# Add or update a device in the Mosquitto password file.
#
# MQTT auth on port 8883:
#   username = device_id (string)
#   password = device access_token from PostgreSQL
#
# Usage (from repo root):
#   ./mosquitto/scripts/add_device.sh <device_id> <access_token>
#
# Example:
#   ./mosquitto/scripts/add_device.sh 67 sim_device_12345_123456789
#
# Run inside the running Mosquitto container (no local mosquitto_passwd required):
#   docker compose exec mosquitto /mosquitto/scripts/add_device.sh 67 YOUR_TOKEN
#
# Or from the host (delegates to the container):
#   docker compose exec mosquitto mosquitto_passwd -b /mosquitto/config/passwd DEVICE_ID TOKEN

set -euo pipefail

DEVICE_ID="${1:-}"
TOKEN="${2:-}"

if [[ -z "${DEVICE_ID}" || -z "${TOKEN}" ]]; then
  echo "Usage: $0 <device_id> <access_token>" >&2
  exit 1
fi

PASSWD_FILE="/mosquitto/config/passwd"

if [[ -f /mosquitto/config/mosquitto.conf ]]; then
  # Running inside the Mosquitto container
  mosquitto_passwd -b "${PASSWD_FILE}" "${DEVICE_ID}" "${TOKEN}"
else
  # Host: delegate to Docker Compose
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
  REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
  cd "${REPO_ROOT}"
  docker compose exec mosquitto mosquitto_passwd -b "${PASSWD_FILE}" "${DEVICE_ID}" "${TOKEN}"
fi

echo "MQTT credentials updated for device_id=${DEVICE_ID}"

# Mosquitto 2.x loads password_file at startup; reload after update.
if [[ -f /mosquitto/config/mosquitto.conf ]]; then
  kill -HUP 1 2>/dev/null || true
else
  docker compose kill -s HUP mosquitto 2>/dev/null || true
fi
