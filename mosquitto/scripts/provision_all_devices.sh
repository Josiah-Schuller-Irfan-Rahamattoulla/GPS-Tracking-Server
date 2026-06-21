#!/usr/bin/env bash
# Provision MQTT passwd + ACL for every device in PostgreSQL.
#
# Usage (repo root, API container or host with DATABASE_URI + docker compose):
#   DATABASE_URI=postgresql://... ./mosquitto/scripts/provision_all_devices.sh
#
# Requires: psql, docker compose (for Mosquitto HUP), add_device.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "${REPO_ROOT}"

if [[ -z "${DATABASE_URI:-}" ]]; then
  echo "Set DATABASE_URI (postgresql://...)" >&2
  exit 1
fi

echo "Loading devices from database..."
psql "${DATABASE_URI}" -At -c "SELECT device_id, access_token FROM devices ORDER BY device_id" |
while IFS='|' read -r device_id token; do
  if [[ -z "${device_id}" || -z "${token}" ]]; then
    continue
  fi
  echo "Provisioning device_id=${device_id}"
  "${SCRIPT_DIR}/add_device.sh" "${device_id}" "${token}"
done

echo "Done. Reload Mosquitto if add_device.sh did not HUP already."
