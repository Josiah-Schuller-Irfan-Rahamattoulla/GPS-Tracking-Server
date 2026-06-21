"""
Publish device control updates to Mosquitto (internal port 1883).

Cellular devices subscribe on TLS port 8883 with username=device_id and
password=access_token. Payload matches device_control_response JSON so
firmware can reuse controls_parse_json().
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import threading
import time
from typing import Any

import paho.mqtt.client as mqtt

logger = logging.getLogger(__name__)

_client: mqtt.Client | None = None
_client_lock = threading.Lock()


def mqtt_enabled() -> bool:
    flag = os.getenv("MQTT_ENABLED", "1").strip().lower()
    return flag not in ("0", "false", "no", "off")


def controls_topic(device_id: int) -> str:
    prefix = os.getenv("MQTT_TOPIC_PREFIX", "devices").strip("/")
    suffix = os.getenv("MQTT_CONTROLS_TOPIC_SUFFIX", "controls").strip("/")
    return f"{prefix}/{device_id}/{suffix}"


def build_controls_payload(device_id: int, control_data: dict[str, Any]) -> dict[str, Any]:
    """Build MQTT JSON payload aligned with WebSocket device_control_response."""
    message: dict[str, Any] = {
        "type": "device_control_response",
        "device_id": device_id,
        "timestamp": int(time.time() * 1000),
    }
    for key in (
        "control_1",
        "control_2",
        "control_3",
        "control_4",
        "control_version",
        "last_applied_control_version",
        "command_pending",
        "command_recovery_interval_ms",
        "controls_updated_at",
        "reset_token",
        "reset_applied_token",
    ):
        if key in control_data:
            message[key] = control_data[key]
    if "data" not in message:
        message["data"] = control_data
    return message


def _mqtt_host() -> str:
    return os.getenv("MQTT_HOST", "mosquitto").strip()


def _mqtt_port() -> int:
    return int(os.getenv("MQTT_PORT", "1883"))


def _connect_client() -> mqtt.Client | None:
    global _client

    if not mqtt_enabled():
        return None

    with _client_lock:
        if _client is not None and _client.is_connected():
            return _client

        client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id=os.getenv("MQTT_CLIENT_ID", "gps-tracking-api"),
        )
        keepalive = int(os.getenv("MQTT_KEEPALIVE_SEC", "60"))
        host = _mqtt_host()
        port = _mqtt_port()

        try:
            client.connect(host, port, keepalive=keepalive)
            client.loop_start()
            _client = client
            logger.info("MQTT publisher connected host=%s port=%s", host, port)
            return _client
        except Exception as exc:
            logger.warning("MQTT publisher connect failed host=%s port=%s err=%s", host, port, exc)
            try:
                client.loop_stop()
            except Exception:
                pass
            _client = None
            return None


def publish_device_controls(device_id: int, control_data: dict[str, Any]) -> bool:
    """
    Publish current controls to the device topic (QoS 1, retained).

    Retained so a device subscribing after an offline period receives the latest state
    (MQTT equivalent of the WebSocket welcome message).
    """
    if not mqtt_enabled():
        return False

    client = _connect_client()
    if client is None:
        return False

    topic = controls_topic(device_id)
    payload_obj = build_controls_payload(device_id, control_data)
    payload = json.dumps(payload_obj, separators=(",", ":"))
    qos = int(os.getenv("MQTT_CONTROLS_QOS", "1"))
    retain = os.getenv("MQTT_CONTROLS_RETAIN", "1").strip().lower() not in ("0", "false", "no")

    try:
        info = client.publish(topic, payload, qos=qos, retain=retain)
        info.wait_for_publish(timeout=float(os.getenv("MQTT_PUBLISH_TIMEOUT_SEC", "5")))
        logger.info(
            "MQTT controls published device_id=%s topic=%s bytes=%s retain=%s",
            device_id,
            topic,
            len(payload),
            retain,
        )
        return True
    except Exception as exc:
        logger.warning("MQTT controls publish failed device_id=%s topic=%s err=%s", device_id, topic, exc)
        return False


async def publish_device_controls_async(device_id: int, control_data: dict[str, Any]) -> bool:
    return await asyncio.to_thread(publish_device_controls, device_id, control_data)


def mqtt_status() -> dict[str, Any]:
    connected = _client is not None and _client.is_connected()
    return {
        "enabled": mqtt_enabled(),
        "connected": connected,
        "host": _mqtt_host(),
        "port": _mqtt_port(),
        "topic_example": controls_topic(0),
    }
