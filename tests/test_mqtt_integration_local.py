"""
Local Docker MQTT integration test (requires running stack).

Run:
  docker compose up -d
  docker compose exec mosquitto mosquitto_passwd -c -b /mosquitto/config/passwd 67 local_test_token
  pytest tests/test_mqtt_integration_local.py -q
"""

from __future__ import annotations

import json
import os
import ssl
import subprocess
import sys
import threading
import time

import paho.mqtt.client as mqtt
import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CA_PATH = os.path.join(REPO_ROOT, "mosquitto", "config", "certs", "ca.crt")
DEVICE_ID = "67"
TOKEN = "local_test_token"
TOPIC = f"devices/{DEVICE_ID}/controls"
HOST = os.getenv("MQTT_TEST_HOST", "127.0.0.1")
PORT = int(os.getenv("MQTT_TEST_PORT", "8883"))


def _stack_available() -> bool:
    if not os.path.isfile(CA_PATH):
        return False
    try:
        import socket

        with socket.create_connection((HOST, PORT), timeout=2):
            return True
    except OSError:
        return False


def _provision_test_device() -> None:
    compose = ["docker", "compose", "-f", os.path.join(REPO_ROOT, "docker-compose.yml")]
    result = subprocess.run(
        [
            *compose,
            "exec",
            "-T",
            "mosquitto",
            "sh",
            "-c",
            f"touch /mosquitto/config/passwd && "
            f"mosquitto_passwd -b /mosquitto/config/passwd {DEVICE_ID} {TOKEN}",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr or result.stdout

    acl_py = f"from api.services.mqtt_provision import upsert_device_acl; upsert_device_acl({DEVICE_ID})"
    acl = subprocess.run(
        [*compose, "exec", "-T", "api", "python", "-c", acl_py],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert acl.returncode == 0, acl.stderr or acl.stdout

    reload = subprocess.run(
        [*compose, "kill", "-s", "HUP", "mosquitto"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert reload.returncode == 0, reload.stderr or reload.stdout
    time.sleep(1)


@pytest.mark.skipif(not _stack_available(), reason="Local Mosquitto not reachable on 8883")
def test_mqtt_controls_publish_and_subscribe():
    _provision_test_device()
    received: list[str] = []
    connected = threading.Event()

    def on_connect(client, userdata, flags, reason_code, properties=None):
        assert reason_code == 0, f"MQTT connect failed rc={reason_code}"
        client.subscribe(TOPIC, qos=1)
        connected.set()

    def on_message(client, userdata, msg):
        received.append(msg.payload.decode())

    sub = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id="pytest-mqtt-sub",
    )
    sub.username_pw_set(username=DEVICE_ID, password=TOKEN)
    sub.tls_set(ca_certs=CA_PATH, cert_reqs=ssl.CERT_REQUIRED)
    sub.on_connect = on_connect
    sub.on_message = on_message
    sub.connect(HOST, PORT, keepalive=30)
    sub.loop_start()

    assert connected.wait(timeout=10), "MQTT subscriber did not connect"

    compose = ["docker", "compose", "-f", os.path.join(REPO_ROOT, "docker-compose.yml")]
    publish_py = (
        "from api.services.mqtt_client import publish_device_controls; "
        "ok = publish_device_controls(67, {"
        "'control_1': True, 'control_2': False, 'control_version': 99, "
        "'last_applied_control_version': 98, 'command_pending': True}); "
        "raise SystemExit(0 if ok else 1)"
    )
    result = subprocess.run(
        [*compose, "exec", "-T", "api", "python", "-c", publish_py],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr or result.stdout

    deadline = time.time() + 10
    while time.time() < deadline and not received:
        time.sleep(0.2)

    sub.loop_stop()
    sub.disconnect()

    assert received, "No MQTT message received on subscriber"
    payload = json.loads(received[-1])
    assert payload["type"] == "device_control_response"
    assert payload["device_id"] == 67
    assert payload["control_1"] is True
    assert payload["control_version"] == 99


def _ensure_test_device_in_db() -> None:
    compose = ["docker", "compose", "-f", os.path.join(REPO_ROOT, "docker-compose.yml")]
    sql = (
        f"INSERT INTO devices (device_id, access_token, sms_number) "
        f"VALUES ({DEVICE_ID}, '{TOKEN}', '+15550000067') "
        f"ON CONFLICT (device_id) DO UPDATE SET access_token = EXCLUDED.access_token;"
    )
    result = subprocess.run(
        [
            *compose,
            "exec",
            "-T",
            "db",
            "psql",
            "-U",
            "gpsuser",
            "-d",
            "gps_tracking",
            "-c",
            sql,
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr or result.stdout


@pytest.mark.skipif(not _stack_available(), reason="Local Mosquitto not reachable on 8883")
def test_mqtt_location_uplink_ingested():
    _provision_test_device()
    _ensure_test_device_in_db()

    test_lat = -33.12345
    test_lon = 151.67890
    location_topic = f"devices/{DEVICE_ID}/location"
    payload = json.dumps(
        {
            "latitude": test_lat,
            "longitude": test_lon,
            "speed": 5.0,
            "timestamp": int(time.time() * 1000),
        }
    )

    pub = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id="pytest-mqtt-loc-pub",
    )
    pub.username_pw_set(username=DEVICE_ID, password=TOKEN)
    pub.tls_set(ca_certs=CA_PATH, cert_reqs=ssl.CERT_REQUIRED)
    pub.connect(HOST, PORT, keepalive=30)
    pub.loop_start()
    time.sleep(0.5)

    result = pub.publish(location_topic, payload, qos=1)
    result.wait_for_publish(timeout=10)
    pub.loop_stop()
    pub.disconnect()

    deadline = time.time() + 15
    row = ""
    compose = ["docker", "compose", "-f", os.path.join(REPO_ROOT, "docker-compose.yml")]
    while time.time() < deadline:
        check = subprocess.run(
            [
                *compose,
                "exec",
                "-T",
                "db",
                "psql",
                "-U",
                "gpsuser",
                "-d",
                "gps_tracking",
                "-t",
                "-A",
                "-c",
                f"SELECT COUNT(*) FROM gps_data WHERE device_id = {DEVICE_ID} "
                f"AND abs(latitude - ({test_lat})) < 0.0001 "
                f"AND abs(longitude - ({test_lon})) < 0.0001;",
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert check.returncode == 0, check.stderr or check.stdout
        row = (check.stdout or "").strip()
        if row == "1":
            break
        time.sleep(0.5)

    assert row == "1", f"Expected GPS row for lat={test_lat} lon={test_lon}, got {row!r}"
