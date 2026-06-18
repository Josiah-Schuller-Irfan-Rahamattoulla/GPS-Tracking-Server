# Mosquitto MQTT (killswitch push)

Eclipse Mosquitto provides **push** killswitch delivery to nRF9151 devices on **port 8883 (TLS)**.
FastAPI publishes internally on **port 1883** (Docker network only, no TLS).

## Quick start

```bash
# 1) Generate TLS certs (once per deploy; default validity 825 days)
./mosquitto/scripts/generate_certs.sh

# 2) Start stack (includes Mosquitto)
docker compose up -d --build

# 3) Provision a device for MQTT auth (run when registering a new device)
./mosquitto/scripts/add_device.sh 67 YOUR_DEVICE_ACCESS_TOKEN

# 4) Verify broker (subscribe on TLS port)
python test_mqtt.py --device-id test_device --token test_token --ca mosquitto/config/certs/ca.crt
```

## Ports

| Port | Exposure | TLS | Auth | Client |
|------|----------|-----|------|--------|
| 1883 | Docker internal only | No | Anonymous | FastAPI (`mqtt_client.py`) |
| 8883 | Host + public | Yes | `passwd` file | nRF9151 firmware |

## Topic

```
devices/{device_id}/killswitch
```

QoS **1** — broker persists until the device acknowledges (or queues offline).

Payload (JSON):

```json
{"command": "kill", "device_id": "67", "timestamp": "2026-06-18T12:00:00+00:00"}
```

## Certificate validity

`generate_certs.sh` defaults to **825 days** (~27 months). For long-lived lab certs:

```bash
./mosquitto/scripts/generate_certs.sh 3650
```

Production: replace with CA-signed certs and rotate before expiry.

## Add device credentials (inside container)

```bash
docker compose exec mosquitto mosquitto_passwd -b /mosquitto/config/passwd 67 YOUR_ACCESS_TOKEN
docker compose restart mosquitto   # only if broker was already running with old passwd
```

Or use the wrapper script from the host (see `mosquitto/scripts/add_device.sh`).
