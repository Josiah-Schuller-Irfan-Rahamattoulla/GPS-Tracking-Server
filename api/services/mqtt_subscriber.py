"""
MQTT subscriber — device uplink (location, ACKs, A-GNSS requests) on internal broker port 1883.
"""

from __future__ import annotations

import logging
import os
import threading

import paho.mqtt.client as mqtt

from api.services.mqtt_client import mqtt_enabled
from api.services.mqtt_handler import handle_mqtt_message
from api.services.mqtt_topics import device_uplink_subscriptions

logger = logging.getLogger(__name__)

_subscriber: mqtt.Client | None = None
_subscriber_lock = threading.Lock()
_subscriber_running = False


def _mqtt_host() -> str:
    return os.getenv("MQTT_HOST", "mosquitto").strip()


def _mqtt_port() -> int:
    return int(os.getenv("MQTT_PORT", "1883"))


def _on_connect(client, userdata, flags, reason_code, properties=None):
    if reason_code != 0:
        logger.error("MQTT subscriber connect failed rc=%s", reason_code)
        return
    for topic, qos in device_uplink_subscriptions():
        client.subscribe(topic, qos=qos)
        logger.info("MQTT subscriber subscribed topic=%s qos=%s", topic, qos)


def _on_message(client, userdata, msg):
    try:
        handle_mqtt_message(msg.topic, msg.payload)
    except Exception as exc:
        logger.exception("MQTT subscriber handler error topic=%s err=%s", msg.topic, exc)


def start_mqtt_subscriber() -> None:
    global _subscriber, _subscriber_running

    if not mqtt_enabled():
        logger.info("MQTT subscriber disabled")
        return

    with _subscriber_lock:
        if _subscriber_running:
            return

        client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id=os.getenv("MQTT_SUBSCRIBER_CLIENT_ID", "gps-tracking-api-sub"),
        )
        client.on_connect = _on_connect
        client.on_message = _on_message

        try:
            client.connect(_mqtt_host(), _mqtt_port(), keepalive=int(os.getenv("MQTT_KEEPALIVE_SEC", "60")))
            client.loop_start()
            _subscriber = client
            _subscriber_running = True
            logger.info("MQTT subscriber started host=%s port=%s", _mqtt_host(), _mqtt_port())
        except Exception as exc:
            logger.warning("MQTT subscriber start failed err=%s", exc)
            try:
                client.loop_stop()
            except Exception:
                pass


def stop_mqtt_subscriber() -> None:
    global _subscriber, _subscriber_running

    with _subscriber_lock:
        if not _subscriber_running or _subscriber is None:
            return
        try:
            _subscriber.loop_stop()
            _subscriber.disconnect()
        except Exception as exc:
            logger.warning("MQTT subscriber stop err=%s", exc)
        _subscriber = None
        _subscriber_running = False
        logger.info("MQTT subscriber stopped")


def subscriber_running() -> bool:
    return _subscriber_running
