# Mosquitto MQTT (device controls push)

Eclipse Mosquitto delivers **control updates** (kill switch, horn, etc.) to nRF9151 devices over **MQTT/TLS on port 8883**. FastAPI publishes on the internal Docker network (port 1883, no TLS).

This replaces the need for a **persistent device WebSocket** for controls, which keeps the LTE modem in RRC connected mode and blocks GNSS on nRF9151.

## Quick start (local Docker)

```bash
# 1) Generate TLS certs (once per deploy)
./mosquitto/scripts/generate_certs.sh

# 2) Start stack (includes Mosquitto + API MQTT publisher)
docker compose up -d --build

# 3) Provision an existing device (username = device_id, password = access_token)
./mosquitto/scripts/add_device.sh 67 YOUR_DEVICE_ACCESS_TOKEN

# 4) Subscribe as the device (TLS) — then PUT controls from app and watch messages arrive
python test_mqtt.py --device-id 67 --token YOUR_DEVICE_ACCESS_TOKEN --ca mosquitto/config/certs/ca.crt
```

New devices registered via `POST /v1/registerDevice` are added to the Mosquitto password file automatically when `MQTT_ENABLED=1`.

## Ports

| Port | Exposure | TLS | Auth | Client |
|------|----------|-----|------|--------|
| 1883 | Docker internal only | No | Anonymous | FastAPI (`mqtt_client.py`) |
| 8883 | Host + public | Yes | `passwd` file | nRF9151 firmware |

**Production:** open **8883/TCP** on your security group / firewall (and optionally put it behind a dedicated hostname, e.g. `mqtt.gpstracking.example.com`).

## Topic

```
devices/{device_id}/controls
```

QoS **1**, **retained** — latest control state is delivered to devices that connect or wake on eDRX after being offline (MQTT equivalent of the WebSocket welcome message).

Payload (JSON, same shape as WebSocket `device_control_response`):

```json
{
  "type": "device_control_response",
  "device_id": 67,
  "control_1": true,
  "control_2": false,
  "control_3": false,
  "control_4": false,
  "control_version": 12,
  "last_applied_control_version": 11,
  "command_pending": true,
  "controls_updated_at": "2026-06-18T12:00:00+00:00",
  "reset_token": 0,
  "reset_applied_token": 0,
  "timestamp": 1718708400000
}
```

Firmware can parse this with the existing `controls_parse_json()` helper.

## Server flow

1. App user `PUT /v1/devices/{id}/controls` → DB update
2. Server broadcasts to WebSocket rooms (unchanged — app/website UI sync)
3. Server publishes retained MQTT message to `devices/{id}/controls`

Reset requests (`POST /v1/devices/{id}/reset`) follow the same path via `broadcast_device_control_response`.

## Environment (API container)

| Variable | Default | Purpose |
|----------|---------|---------|
| `MQTT_ENABLED` | `1` | Set `0` to disable publish/provision |
| `MQTT_HOST` | `mosquitto` | Internal broker hostname |
| `MQTT_PORT` | `1883` | Internal publish port |
| `MQTT_PASSWD_FILE` | `/mosquitto/config/passwd` | Shared with Mosquitto container |

## Certificate validity

`generate_certs.sh` defaults to **825 days** (~27 months). For long-lived lab certs:

```bash
./mosquitto/scripts/generate_certs.sh 3650
```

Production: replace with CA-signed certs and rotate before expiry. Embed `ca.crt` in nRF9151 firmware for broker verification.

## Add device credentials manually

```bash
./mosquitto/scripts/add_device.sh 67 YOUR_ACCESS_TOKEN
# or inside container:
docker compose exec mosquitto /mosquitto/scripts/add_device.sh 67 YOUR_ACCESS_TOKEN
```

## Verify end-to-end

1. Terminal A: `python test_mqtt.py --device-id 67 --token TOKEN --ca mosquitto/config/certs/ca.crt --wait-sec 120`
2. Terminal B: `PUT /v1/devices/67/controls` (app or curl)
3. Terminal A should print the retained control payload within a second

Check API logs for `MQTT controls published device_id=67`.
