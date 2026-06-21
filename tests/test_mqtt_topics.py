"""Unit tests for MQTT topic helpers."""

from api.services.mqtt_topics import (
    agnss_data_topic,
    agnss_request_topic,
    control_ack_topic,
    controls_topic,
    device_uplink_subscriptions,
    location_topic,
    parse_device_id_from_topic,
    reset_ack_topic,
)


def test_device_topics_default():
    assert controls_topic(67) == "devices/67/controls"
    assert location_topic(67) == "devices/67/location"
    assert control_ack_topic(67) == "devices/67/control_ack"
    assert reset_ack_topic(67) == "devices/67/reset_ack"
    assert agnss_request_topic(67) == "devices/67/agnss_request"
    assert agnss_data_topic(67) == "devices/67/agnss_data"


def test_uplink_subscriptions():
    topics = {t for t, _ in device_uplink_subscriptions()}
    assert topics == {
        "devices/+/location",
        "devices/+/control_ack",
        "devices/+/reset_ack",
        "devices/+/agnss_request",
    }


def test_parse_device_id_from_topic():
    assert parse_device_id_from_topic("devices/67/location") == 67
    assert parse_device_id_from_topic("devices/abc/location") is None
    assert parse_device_id_from_topic("bad") is None
