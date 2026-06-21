"""
Process MQTT uplink messages from devices (location, control ACK, reset ACK).

Topic device_id is trusted when messages arrive on 8883 with per-device ACL auth.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from psycopg2 import connect

from api.db.devices import ack_device_controls_applied, ack_device_reset
from api.endpoints.realtime_endpoints import (
    broadcast_control_applied_to_users,
    broadcast_geofence_breach,
    broadcast_location_update,
)
from api.services.device_ingest import ingest_location
from api.services.mqtt_topics import parse_device_id_from_topic

logger = logging.getLogger(__name__)

_main_loop: asyncio.AbstractEventLoop | None = None


def set_event_loop(loop: asyncio.AbstractEventLoop) -> None:
    global _main_loop
    _main_loop = loop


def _schedule(coro) -> None:
    if _main_loop is None or not _main_loop.is_running():
        logger.warning("MQTT handler: no event loop; dropping async broadcast")
        return
    asyncio.run_coroutine_threadsafe(coro, _main_loop)


def _payload_dict(raw: bytes) -> dict[str, Any]:
    data = json.loads(raw.decode("utf-8"))
    if not isinstance(data, dict):
        raise ValueError("MQTT payload must be a JSON object")
    return data


def _unwrap_data(payload: dict[str, Any]) -> dict[str, Any]:
    """Accept flat fields or WebSocket-style {\"data\": {...}}."""
    inner = payload.get("data")
    if isinstance(inner, dict):
        merged = dict(inner)
        for key in ("device_id", "type", "timestamp"):
            if key in payload and key not in merged:
                merged[key] = payload[key]
        return merged
    return payload


def handle_mqtt_message(topic: str, payload_raw: bytes) -> None:
    device_id = parse_device_id_from_topic(topic)
    if device_id is None:
        logger.warning("MQTT ignored unknown topic=%s", topic)
        return

    suffix = topic.split("/")[-1]
    try:
        payload = _payload_dict(payload_raw)
    except (json.JSONDecodeError, ValueError) as exc:
        logger.warning("MQTT invalid JSON topic=%s err=%s", topic, exc)
        return

    if suffix == "location":
        _handle_location(device_id, payload)
    elif suffix == "control_ack":
        _handle_control_ack(device_id, payload)
    elif suffix == "reset_ack":
        _handle_reset_ack(device_id, payload)
    else:
        logger.debug("MQTT unhandled suffix=%s topic=%s", suffix, topic)


def _handle_location(device_id: int, payload: dict[str, Any]) -> None:
    body = _unwrap_data(payload)
    if body.get("device_id") is not None and int(body["device_id"]) != device_id:
        logger.warning("MQTT location device_id mismatch topic=%s payload=%s", device_id, body.get("device_id"))
        return

    try:
        location_data, breach_events = ingest_location(device_id, body)
    except Exception as exc:
        logger.warning("MQTT location ingest failed device_id=%s err=%s", device_id, exc)
        return

    logger.info(
        "MQTT location ingested device_id=%s lat=%.5f lon=%.5f",
        device_id,
        location_data["latitude"],
        location_data["longitude"],
    )

    async def _broadcast():
        await broadcast_location_update(device_id, location_data)
        for breach in breach_events:
            await broadcast_geofence_breach(
                device_id,
                breach.geofence_id,
                {
                    "device_id": device_id,
                    "geofence_id": breach.geofence_id,
                    "breach_type": breach.breach_type,
                    "latitude": location_data["latitude"],
                    "longitude": location_data["longitude"],
                    "timestamp": location_data.get("created_at", ""),
                },
            )

    _schedule(_broadcast())


def _handle_control_ack(device_id: int, payload: dict[str, Any]) -> None:
    body = _unwrap_data(payload)
    version = body.get("applied_control_version")
    if version is None:
        version = body.get("last_applied_control_version")
    if version is None:
        logger.warning("MQTT control_ack missing version device_id=%s", device_id)
        return

    applied = int(version)
    if applied < 0:
        logger.warning("MQTT control_ack invalid version device_id=%s", device_id)
        return

    import os

    db_conn = connect(dsn=os.getenv("DATABASE_URI"))
    try:
        updated = ack_device_controls_applied(
            db_conn=db_conn,
            device_id=device_id,
            applied_control_version=applied,
        )
    finally:
        db_conn.close()

    if not updated:
        logger.warning("MQTT control_ack device not found device_id=%s", device_id)
        return

    logger.info("MQTT control_ack device_id=%s version=%s", device_id, applied)
    _schedule(broadcast_control_applied_to_users(device_id, updated))


def _handle_reset_ack(device_id: int, payload: dict[str, Any]) -> None:
    body = _unwrap_data(payload)
    token = body.get("reset_token")
    if token is None:
        logger.warning("MQTT reset_ack missing token device_id=%s", device_id)
        return

    reset_token = int(token)
    if reset_token <= 0:
        logger.warning("MQTT reset_ack invalid token device_id=%s", device_id)
        return

    import os

    db_conn = connect(dsn=os.getenv("DATABASE_URI"))
    try:
        updated = ack_device_reset(
            db_conn=db_conn,
            device_id=device_id,
            reset_token=reset_token,
        )
    finally:
        db_conn.close()

    if not updated:
        logger.warning("MQTT reset_ack device not found device_id=%s", device_id)
        return

    logger.info("MQTT reset_ack device_id=%s token=%s", device_id, reset_token)
