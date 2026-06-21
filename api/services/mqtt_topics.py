"""MQTT topic layout for device ↔ server messaging."""

from __future__ import annotations

import os


def topic_prefix() -> str:
    return os.getenv("MQTT_TOPIC_PREFIX", "devices").strip("/")


def device_topic(device_id: int, suffix: str) -> str:
    return f"{topic_prefix()}/{device_id}/{suffix.strip('/')}"


def controls_topic(device_id: int) -> str:
    suffix = os.getenv("MQTT_CONTROLS_TOPIC_SUFFIX", "controls")
    return device_topic(device_id, suffix)


def location_topic(device_id: int) -> str:
    return device_topic(device_id, os.getenv("MQTT_LOCATION_TOPIC_SUFFIX", "location"))


def control_ack_topic(device_id: int) -> str:
    return device_topic(device_id, os.getenv("MQTT_CONTROL_ACK_TOPIC_SUFFIX", "control_ack"))


def reset_ack_topic(device_id: int) -> str:
    return device_topic(device_id, os.getenv("MQTT_RESET_ACK_TOPIC_SUFFIX", "reset_ack"))


def device_uplink_subscriptions() -> list[tuple[str, int]]:
    """Wildcard subscriptions for the API MQTT bridge (internal broker)."""
    prefix = topic_prefix()
    qos = int(os.getenv("MQTT_UPLINK_QOS", "1"))
    return [
        (f"{prefix}/+/location", qos),
        (f"{prefix}/+/control_ack", qos),
        (f"{prefix}/+/reset_ack", qos),
    ]


def parse_device_id_from_topic(topic: str) -> int | None:
    parts = topic.split("/")
    if len(parts) < 3:
        return None
    try:
        return int(parts[1])
    except ValueError:
        return None
