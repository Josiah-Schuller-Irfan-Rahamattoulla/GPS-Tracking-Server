# Production MQTT setup (gpstracking.josiahschuller.au)

## Start here (plain language)

Your tracker needs **three things** to use MQTT in production:

| Piece | What it is | Status today |
|-------|------------|--------------|
| **1. MQTT broker (Mosquitto)** | A small program that receives GPS from devices and sends kill-switch commands. Runs next to your API. | **Not running** on production |
| **2. Port 8883 open** | Cellular devices connect to `gpstracking.josiahschuller.au:8883` (like HTTPS uses 443). | **Blocked** — connection times out |
| **3. Firmware trusts the broker** | The tracker must know which TLS certificate to trust for MQTT (different from HTTPS). | **Fixed in firmware** — uses Mosquitto CA on sec tag 43; re-flash after server certs are final |

**What “ECS sidecar” means (option a):** Your API runs in AWS ECS as a container. A **sidecar** is a second container in the **same task** — Mosquitto runs beside the API, shares a folder for passwords/certs, and exposes port 8883. See [ecs-task-mqtt-sidecar.example.json](./ecs-task-mqtt-sidecar.example.json).

**What “MQTT CA in firmware” means (option b):** HTTPS uses Amazon’s certificate (already in the tracker). Mosquitto uses its **own** certificate from `generate_certs.sh`. The firmware now stores that Mosquitto CA separately so MQTT TLS works without changing HTTPS.

### What to do next (in order)

1. **Redeploy the API** — GitHub → Actions → “Build and Deploy to AWS” on branch `main` (gets MQTT code into production).
2. **Generate broker certs** (once, on your laptop with Git Bash):
   ```bash
   cd GPS-Tracking-Server
   MQTT_TLS_HOSTNAME=gpstracking.josiahschuller.au ./mosquitto/scripts/generate_certs.sh
   ```
3. **Run Mosquitto in production** — pick one:
   - **Easier:** One EC2 instance, clone repo, `docker compose up -d` (same as local dev).
   - **Keep ECS:** Add Mosquitto sidecar using the example JSON + EFS; add NLB on port 8883.
4. **Open port 8883** in the AWS security group for the host/NLB.
5. **Add your device to Mosquitto** (device ID + access token from the database):
   ```bash
   ./mosquitto/scripts/add_device.sh 67 YOUR_DEVICE_ACCESS_TOKEN
   ```
6. **Verify** — `/health` should show `"mqtt": { "publisher_connected": true, ... }`. Then:
   ```bash
   python test_mqtt.py --host gpstracking.josiahschuller.au --device-id 67 --token TOKEN --ca mosquitto/config/certs/ca.crt
   ```
7. **Flash firmware** with the MQTT build (includes Mosquitto CA). If you regenerate certs in step 2, rebuild firmware so `mqtt_ca_cert.h` matches.

---

Cellular devices connect to **MQTT/TLS on port 8883** at the same hostname as the HTTPS API. The FastAPI service publishes controls and subscribes to uplink on internal port **1883** only.

## Current production status

After merging MQTT to `main`, you still need to **deploy Mosquitto** and open **8883/TCP** in the security group. Until then:

- `https://gpstracking.josiahschuller.au/health` will not include `"mqtt": {...}` (or shows publisher/subscriber disconnected).
- Port **8883** will not accept connections from devices.

Local Docker Compose (`docker compose up`) runs API + Mosquitto together. **ECS today only deploys the API image** — add Mosquitto as a sidecar or second service (see below).

## Checklist

### 1. TLS certificates

From repo root (Git Bash / WSL):

```bash
MQTT_TLS_HOSTNAME=gpstracking.josiahschuller.au ./mosquitto/scripts/generate_certs.sh
```

This writes `mosquitto/config/certs/ca.crt` (device trust anchor) and server cert/key with SAN for the public hostname.

**Firmware TLS:** The tracker embeds **Amazon Root CA 1** for HTTPS (ALB/ACM). Mosquitto uses a **separate CA** from `generate_certs.sh`. For MQTT to work you must either:

- **A (simplest for now):** Flash firmware with `mosquitto/config/certs/ca.crt` embedded as the MQTT trust anchor (separate sec tag or replace for MQTT-only builds), **or**
- **B (production-grade):** Terminate TLS on an **NLB with ACM** using the same public cert as HTTPS, or install an **ACM-exported** cert on Mosquitto so the device’s existing Amazon Root CA still validates the broker.

### 2. Run Mosquitto alongside the API

**Docker Compose (single host / EC2):**

```bash
docker compose up -d --build
```

Ensure `8883:8883` is published and the host firewall / security group allows **8883/TCP** from the internet (cellular devices have dynamic IPs).

**ECS (recommended pattern):** See [ecs-task-mqtt-sidecar.example.json](./ecs-task-mqtt-sidecar.example.json) for a copy-paste starting point.

1. Add a **second container** in the task definition: `eclipse-mosquitto:2` with the same task, sharing an **EFS** or bind mount for:
   - `/mosquitto/config/passwd`
   - `/mosquitto/config/acl`
   - `/mosquitto/data/certs`
2. Map container port **8883** to the host or attach an **NLB target group** on 8883.
3. Set API env vars:
   - `MQTT_ENABLED=1`
   - `MQTT_HOST=localhost` (if sidecar on same task) or the Mosquitto service discovery name
   - `MQTT_PORT=1883`
   - `MQTT_PASSWD_FILE=/mosquitto/config/passwd`
   - `MQTT_ACL_FILE=/mosquitto/config/acl`
4. Mount the same `passwd` / `acl` paths into **both** API and Mosquitto containers.

After deploy, `/health` should include:

```json
{
  "server": "healthy",
  "database": "healthy",
  "mqtt": {
    "enabled": true,
    "publisher_connected": true,
    "subscriber_connected": true
  }
}
```

### 3. Provision existing devices

New devices: `POST /v1/registerDevice` auto-provisions MQTT credentials when `MQTT_ENABLED=1` and `mosquitto_passwd` is available in the API container.

**Existing devices** (once Mosquitto is running):

```bash
# One device
./mosquitto/scripts/add_device.sh <device_id> <access_token>

# Or inside the Mosquitto container
docker compose exec mosquitto /mosquitto/scripts/add_device.sh 67 YOUR_TOKEN
```

Reload after bulk edits: `docker compose kill -s HUP mosquitto`

### 4. Verify end-to-end

```bash
python test_mqtt.py --host gpstracking.josiahschuller.au --device-id 67 \
  --token YOUR_DEVICE_TOKEN --ca mosquitto/config/certs/ca.crt
```

From the app/website, `PUT /v1/devices/67/controls` — the test client should receive retained JSON on `devices/67/controls`.

### 5. Deploy API from `main`

GitHub Actions → **Build and Deploy to AWS** (workflow_dispatch). This updates the ECS API image only; ensure Mosquitto is deployed separately if not using full `docker compose` on the host.

## Topic contract

See [mosquitto/README.md](../mosquitto/README.md). Devices use username=`device_id`, password=`access_token`.
