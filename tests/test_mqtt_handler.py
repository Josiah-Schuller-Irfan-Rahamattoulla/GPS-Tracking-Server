"""Unit tests for MQTT uplink handler (no broker or DB)."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from api.services.mqtt_handler import handle_mqtt_message


@patch("api.services.mqtt_handler.ingest_location")
@patch("api.services.mqtt_handler._schedule")
def test_handle_location_flat_payload(mock_schedule, mock_ingest):
    mock_ingest.return_value = (
        {"device_id": 67, "latitude": -33.86, "longitude": 151.20, "created_at": "2026-06-18T00:00:00+00:00"},
        [],
    )

    payload = {"latitude": -33.86, "longitude": 151.20, "speed": 12.5}
    handle_mqtt_message("devices/67/location", json.dumps(payload).encode())

    mock_ingest.assert_called_once()
    assert mock_ingest.call_args[0][0] == 67
    assert mock_ingest.call_args[0][1]["latitude"] == -33.86
    mock_schedule.assert_called_once()


@patch("api.services.mqtt_handler.ingest_location")
@patch("api.services.mqtt_handler._schedule")
def test_handle_location_ws_style_data_wrapper(mock_schedule, mock_ingest):
    mock_ingest.return_value = (
        {"device_id": 67, "latitude": 1.0, "longitude": 2.0, "created_at": "2026-06-18T00:00:00+00:00"},
        [],
    )

    payload = {
        "type": "location_update",
        "device_id": 67,
        "data": {"latitude": 1.0, "longitude": 2.0},
    }
    handle_mqtt_message("devices/67/location", json.dumps(payload).encode())

    body = mock_ingest.call_args[0][1]
    assert body["latitude"] == 1.0
    assert body["longitude"] == 2.0


@patch("api.services.mqtt_handler.ack_device_controls_applied")
@patch("api.services.mqtt_handler.connect")
@patch("api.services.mqtt_handler._schedule")
def test_handle_control_ack(mock_schedule, mock_connect, mock_ack):
    mock_conn = MagicMock()
    mock_connect.return_value = mock_conn
    mock_ack.return_value = {"device_id": 67, "last_applied_control_version": 5}

    handle_mqtt_message(
        "devices/67/control_ack",
        json.dumps({"applied_control_version": 5}).encode(),
    )

    mock_ack.assert_called_once()
    assert mock_ack.call_args.kwargs["applied_control_version"] == 5
    mock_conn.close.assert_called_once()
    mock_schedule.assert_called_once()
