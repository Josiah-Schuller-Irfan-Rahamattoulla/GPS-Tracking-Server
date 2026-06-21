# Mosquitto MQTT (device messaging)

Eclipse Mosquitto handles **all cellular device traffic** over **MQTT/TLS on port 8883**:

- **Downlink (server → device):** controls / kill switch / reset
- **Uplink (device → server):** GPS location batches, control ACK, reset ACK

FastAPI connects on the internal Docker network (port **1883**, no TLS): publishes controls and subscribes to device uplink topics.

This replaces the **persistent device WebSocket**, which keeps the nRF9151 LTE modem in RRC connected mode and blocks GNSS.

**HTTP remains** for bootstrap only: registration, A-GNSS, cell location, optional control poll fallback.

## Quick start (local Docker)

```bash
# 1) Generate TLS certs (once per machine / after clone)
./mosquitto/scripts/ensure_certs.sh
# Or for production hostname:
# MQTT_TLS_HOSTNAME=gpstracking.josiahschuller.au ./mosquitto/scripts/generate_certs.sh

# 2) Start stack (Mosquitto + API MQTT publisher/subscriber)
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
| 1883 | Docker internal only | No | Anonymous | FastAPI (`mqtt_client.py`, `mqtt_subscriber.py`) |
| 8883 | Host + public | Yes | `passwd` + ACL | nRF9151 firmware |

**Production:** open **8883/TCP** on your security group / firewall.

## Topic contract

Prefix defaults to `devices` (override with `MQTT_TOPIC_PREFIX`).

| Direction | Topic | QoS | Retain | Payload |
|-----------|-------|-----|--------|---------|
| Server → device | `devices/{id}/controls` | 1 | **yes** | `device_control_response` JSON |
| Device → server | `devices/{id}/location` | 1 | no | GPS point (flat or `{data:{...}}`) |
| Device → server | `devices/{id}/control_ack` | 1 | no | `{"applied_control_version": N}` |
| Device → server | `devices/{id}/reset_ack` | 1 | no | `{"reset_token": N}` |

### Controls downlink (retained)

Latest control state is delivered to devices that connect or wake on eDRX after being offline.

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

Firmware can parse this with existing `controls_parse_json()`.

### Location uplink

Same fields as HTTP `sendGPSData` / WebSocket `location_update`:

```json
{
  "latitude": -33.8688,
  "longitude": 151.2093,
  "speed": 12.5,
  "heading": 90.0,
  "timestamp": 1718708400000,
  "trip_active": true,
  "voltage": 3.9
}
```

WebSocket-style wrapper is also accepted: `{"type":"location_update","data":{...}}`.

The API ingests location into PostgreSQL and broadcasts to **user** WebSockets (app/website map) — unchanged.

## ACL (port 8883)

Each device gets an explicit ACL block (not wildcards — Mosquitto pattern ACL did not work reliably in testing):

```
user 67
topic read devices/67/controls
topic write devices/67/location
topic write devices/67/control_ack
topic write devices/67/reset_ack
```

Blocks are written automatically by:

- `POST /v1/registerDevice` → `mqtt_provision.py`
- `./mosquitto/scripts/add_device.sh` (host, requires bash)
- Integration tests → `upsert_device_acl()` via API container

After manual passwd/acl edits, reload Mosquitto: `docker compose kill -s HUP mosquitto`

Internal port **1883** stays anonymous (API bridge only; not exposed on the host).

## Server flow

**Controls**

1. App user `PUT /v1/devices/{id}/controls` → DB update
2. Server broadcasts to user WebSocket rooms (app UI)
3. Server publishes retained MQTT to `devices/{id}/controls`

**Location**

1. Device publishes to `devices/{id}/location` on 8883
2. API subscriber on 1883 receives → `ingest_location()` → DB
3. Server broadcasts to user WebSocket rooms

**ACKs**

Device publishes `control_ack` / `reset_ack` instead of sending over device WebSocket.

## Environment (API container)

| Variable | Default | Purpose |
|----------|---------|---------|
| `MQTT_ENABLED` | `1` | Set `0` to disable publish/subscribe/provision |
| `MQTT_HOST` | `mosquitto` | Internal broker hostname |
| `MQTT_PORT` | `1883` | Internal port |
| `MQTT_PASSWD_FILE` | `/mosquitto/config/passwd` | Shared with Mosquitto container |
| `MQTT_TOPIC_PREFIX` | `devices` | Topic root |
| `MQTT_UPLINK_QOS` | `1` | QoS for uplink subscriptions |

## Certificate validity

`generate_certs.sh` defaults to **825 days** (~27 months). Production: use CA-signed certs; embed `ca.crt` in firmware.

## Verify end-to-end

```bash
pytest tests/test_mqtt_controls.py tests/test_mqtt_topics.py tests/test_mqtt_handler.py -q
pytest tests/test_mqtt_integration_local.py -q   # requires docker compose up
```

1. Terminal A: `python test_mqtt.py --device-id 67 --token TOKEN --ca mosquitto/config/certs/ca.crt`
2. Terminal B: `PUT /v1/devices/67/controls`
3. Terminal A should print the retained control payload

Check API logs for `MQTT controls published` and `MQTT location ingested`.
