"""Unit tests for MQTT uplink handler (no broker or DB)."""

from __future__ import annotations

import json
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

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


@patch("api.services.mqtt_handler.publish_agnss_chunks_async", new_callable=AsyncMock, return_value=True)
@patch("api.services.mqtt_handler.fetch_agnss_bytes", new_callable=AsyncMock, return_value=(b"\x01\x02", "nRF Cloud"))
@patch("api.services.mqtt_handler._schedule")
def test_handle_agnss_request(mock_schedule, mock_fetch, mock_publish):
    handle_mqtt_message(
        "devices/67/agnss_request",
        b'{"mcc":505,"mnc":1,"tac":12345,"eci":67890}',
    )

    mock_schedule.assert_called_once()
    coro = mock_schedule.call_args[0][0]
    asyncio.run(coro)
    mock_fetch.assert_awaited_once()
    assert mock_fetch.call_args.kwargs["mcc"] == 505
    mock_publish.assert_awaited_once_with(67, b"\x01\x02")


@patch("api.services.mqtt_handler.publish_cell_locate_response_async", new_callable=AsyncMock, return_value=True)
@patch("api.services.mqtt_handler._schedule")
def test_handle_cell_locate_request(mock_schedule, mock_publish):
    handle_mqtt_message(
        "devices/67/cell_locate_request",
        json.dumps(
            {
                "device_id": 67,
                "cells": [
                    {
                        "cellId": 12345,
                        "mcc": 505,
                        "mnc": 1,
                        "lac": 100,
                        "tac": 100,
                        "signal": -95,
                    }
                ],
            }
        ).encode(),
    )

    mock_schedule.assert_called_once()
    coro = mock_schedule.call_args[0][0]
    with patch(
        "api.services.cell_locate_service.resolve_cell_location",
        new_callable=AsyncMock,
    ) as mock_resolve:
        mock_resolve.return_value = type(
            "R",
            (),
            {
                "latitude": -33.86,
                "longitude": 151.20,
                "accuracy": 500.0,
                "source": "google",
            },
        )()
        asyncio.run(coro)

    mock_publish.assert_awaited_once()
    payload = mock_publish.call_args[0][1]
    assert payload["latitude"] == -33.86
    assert payload["source"] == "google"
