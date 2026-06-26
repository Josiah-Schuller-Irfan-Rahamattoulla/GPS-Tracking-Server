"""
Publish device control updates to Mosquitto (internal port 1883).

Cellular devices subscribe on TLS port 8883 with username=device_id and
password=access_token. Payload matches device_control_response JSON so
firmware can reuse controls_parse_json().
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import threading
import time
from typing import Any

import paho.mqtt.client as mqtt

from api.services.mqtt_topics import controls_topic, agnss_data_topic, location_topic, cell_locate_response_topic

logger = logging.getLogger(__name__)

_client: mqtt.Client | None = None
_client_lock = threading.Lock()


def mqtt_enabled() -> bool:
    flag = os.getenv("MQTT_ENABLED", "1").strip().lower()
    return flag not in ("0", "false", "no", "off")


def control_data_from_device(device: Any) -> dict[str, Any]:
    """Build MQTT/WS control payload fields from a device row or model."""
    control_version_val = int(getattr(device, "control_version", 0) or 0)
    last_applied_val = int(getattr(device, "last_applied_control_version", 0) or 0)
    command_pending = control_version_val > last_applied_val
    controls_updated_at = getattr(device, "controls_updated_at", None)
    if controls_updated_at is not None and hasattr(controls_updated_at, "isoformat"):
        controls_updated_at = controls_updated_at.isoformat()
    return {
        "device_id": getattr(device, "device_id", None),
        "control_1": getattr(device, "control_1", None),
        "control_2": getattr(device, "control_2", None),
        "control_3": getattr(device, "control_3", None),
        "control_4": getattr(device, "control_4", None),
        "control_version": control_version_val,
        "last_applied_control_version": last_applied_val,
        "command_pending": command_pending,
        "command_recovery_interval_ms": (
            int(os.getenv("COMMAND_RECOVERY_INTERVAL_MS", "5000")) if command_pending else None
        ),
        "controls_updated_at": controls_updated_at,
        "reset_token": int(getattr(device, "reset_token", 0) or 0),
        "reset_applied_token": int(getattr(device, "reset_applied_token", 0) or 0),
        "remote_viewing": bool(getattr(device, "remote_viewing", False) or False),
        "leds_enabled": bool(getattr(device, "leds_enabled", False) or False),
    }


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
        "remote_viewing",
        "leds_enabled",
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


def publish_agnss_chunks(device_id: int, agnss_data: bytes) -> bool:
    """
    Publish A-GNSS binary as chunked JSON on devices/{id}/agnss_data (QoS 1, not retained).

    Each message: {"seq": N, "total": T, "chunk_b64": "..."} with ~768 raw bytes per chunk.
    """
    if not mqtt_enabled() or not agnss_data:
        return False

    client = _connect_client()
    if client is None:
        return False

    chunk_size = int(os.getenv("MQTT_AGNSS_CHUNK_BYTES", "768"))
    topic = agnss_data_topic(device_id)
    qos = int(os.getenv("MQTT_AGNSS_QOS", "1"))
    total = (len(agnss_data) + chunk_size - 1) // chunk_size

    try:
        for seq in range(total):
            start = seq * chunk_size
            chunk = agnss_data[start : start + chunk_size]
            payload_obj = {
                "seq": seq,
                "total": total,
                "chunk_b64": base64.b64encode(chunk).decode("ascii"),
            }
            payload = json.dumps(payload_obj, separators=(",", ":"))
            info = client.publish(topic, payload, qos=qos, retain=False)
            info.wait_for_publish(timeout=float(os.getenv("MQTT_PUBLISH_TIMEOUT_SEC", "5")))
        logger.info(
            "MQTT A-GNSS published device_id=%s topic=%s bytes=%s chunks=%s",
            device_id,
            topic,
            len(agnss_data),
            total,
        )
        return True
    except Exception as exc:
        logger.warning("MQTT A-GNSS publish failed device_id=%s topic=%s err=%s", device_id, topic, exc)
        return False


async def publish_agnss_chunks_async(device_id: int, agnss_data: bytes) -> bool:
    return await asyncio.to_thread(publish_agnss_chunks, device_id, agnss_data)


def publish_cell_locate_response(device_id: int, payload: dict[str, Any]) -> bool:
    """Publish cell locate result on devices/{id}/cell_locate_response (QoS 1)."""
    if not mqtt_enabled():
        return False

    client = _connect_client()
    if client is None:
        return False

    topic = cell_locate_response_topic(device_id)
    qos = int(os.getenv("MQTT_CELL_LOCATE_QOS", "1"))
    body = dict(payload)
    body.setdefault("device_id", device_id)

    try:
        message = json.dumps(body, separators=(",", ":"))
        info = client.publish(topic, message, qos=qos, retain=False)
        info.wait_for_publish(timeout=float(os.getenv("MQTT_PUBLISH_TIMEOUT_SEC", "5")))
        logger.info("MQTT cell_locate_response published device_id=%s topic=%s", device_id, topic)
        return True
    except Exception as exc:
        logger.warning(
            "MQTT cell_locate_response publish failed device_id=%s topic=%s err=%s",
            device_id,
            topic,
            exc,
        )
        return False


async def publish_cell_locate_response_async(device_id: int, payload: dict[str, Any]) -> bool:
    return await asyncio.to_thread(publish_cell_locate_response, device_id, payload)


def mqtt_status() -> dict[str, Any]:
    from api.services.mqtt_subscriber import subscriber_running

    connected = _client is not None and _client.is_connected()
    return {
        "enabled": mqtt_enabled(),
        "publisher_connected": connected,
        "subscriber_running": subscriber_running(),
        "host": _mqtt_host(),
        "port": _mqtt_port(),
        "controls_topic_example": controls_topic(0),
        "location_topic_example": location_topic(0),
    }
