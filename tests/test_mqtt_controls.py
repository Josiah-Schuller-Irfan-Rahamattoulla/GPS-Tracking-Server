"""Unit tests for MQTT controls payload (no broker required)."""

from api.services.mqtt_client import build_controls_payload, controls_topic, mqtt_enabled


def test_controls_topic_default():
    assert controls_topic(67) == "devices/67/controls"


def test_build_controls_payload_includes_control_fields():
    payload = build_controls_payload(
        67,
        {
            "control_1": True,
            "control_2": False,
            "control_3": True,
            "control_4": False,
            "control_version": 9,
            "last_applied_control_version": 8,
            "command_pending": True,
            "reset_token": 3,
        },
    )
    assert payload["type"] == "device_control_response"
    assert payload["device_id"] == 67
    assert payload["control_1"] is True
    assert payload["control_4"] is False
    assert payload["control_version"] == 9
    assert payload["command_pending"] is True
    assert payload["reset_token"] == 3
    assert "timestamp" in payload
    assert payload["data"]["control_1"] is True


def test_mqtt_enabled_default(monkeypatch):
    monkeypatch.delenv("MQTT_ENABLED", raising=False)
    assert mqtt_enabled() is True

    monkeypatch.setenv("MQTT_ENABLED", "0")
    assert mqtt_enabled() is False
