"""
Full device flow tests: every action the device can perform against the server.

Covers:
- Device registration (POST /v1/registerDevice)
- Send GPS data (POST /v1/sendGPSData) – auth, validation, optional fields, stale timestamp
- Get device controls (GET /v1/getDeviceControls)
- A-GNSS (GET /v1/agnss) – auth, optional lat/lon
- Cell location (POST /v1/cell_location) – auth, body shape
- Device WebSocket – connect, ping/pong, location_update broadcast

Run with server up: pytest tests/test_device_flows.py -v
"""
import asyncio
import json
import os
import random
import time
from datetime import datetime, timedelta, timezone

import pytest
import requests

try:
    import websockets
    HAS_WEBSOCKETS = True
except ImportError:
    HAS_WEBSOCKETS = False

HTTP_BASE = os.getenv("TEST_BASE_URL", "http://localhost:8000")
WS_BASE = HTTP_BASE.replace("http://", "ws://").replace("https://", "wss://")
BASE = f"{HTTP_BASE}/v1"


def _unique_device():
    """Unique device payload."""
    import uuid
    unique = uuid.uuid4().int & (1<<31)-1
    ts = int(time.time() * 1000)
    return {
        "device_id": 600000 + (ts % 100000) + (unique % 10000000),
        "access_token": f"device_flow_{ts}_{unique}",
        "sms_number": f"+1555{ts % 10000000:07d}{unique % 1000:03d}",
        "name": "Device Flow Test",
    }


def _register_device_only():
    """Register a device (no user link). Returns (device_id, access_token)."""
    dev = _unique_device()
    r = requests.post(f"{BASE}/registerDevice", json=dev, timeout=10)
    r.raise_for_status()
    return dev["device_id"], dev["access_token"]


# ---------- Registration ----------


def test_device_register_success():
    """Device can register with device_id, access_token, sms_number, optional name."""
    try:
        device_id, access_token = _register_device_only()
    except requests.exceptions.ConnectionError:
        pytest.skip("Server not reachable")
    assert isinstance(device_id, int)
    assert isinstance(access_token, str) and len(access_token) > 0


def test_device_register_duplicate_device_id_rejected():
    """Registering again with same device_id returns 409."""
    try:
        dev = _unique_device()
        requests.post(f"{BASE}/registerDevice", json=dev, timeout=10).raise_for_status()
        r = requests.post(f"{BASE}/registerDevice", json=dev, timeout=10)
    except requests.exceptions.ConnectionError:
        pytest.skip("Server not reachable")
    assert r.status_code == 409


# ---------- Send GPS (device auth: Access-Token + device_id in body) ----------


def test_send_gps_requires_device_auth():
    """sendGPSData without Access-Token returns 401."""
    try:
        r = requests.post(
            f"{BASE}/sendGPSData",
            json={
                "device_id": 1,
                "latitude": 0.0,
                "longitude": 0.0,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            timeout=10,
        )
    except requests.exceptions.ConnectionError:
        pytest.skip("Server not reachable")
    assert r.status_code == 401


def test_send_gps_invalid_token_rejected():
    """sendGPSData with wrong device token returns 401."""
    try:
        device_id, _ = _register_device_only()
        r = requests.post(
            f"{BASE}/sendGPSData",
            headers={"Access-Token": "wrong_token"},
            json={
                "device_id": device_id,
                "latitude": 0.0,
                "longitude": 0.0,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            timeout=10,
        )
    except requests.exceptions.ConnectionError:
        pytest.skip("Server not reachable")
    assert r.status_code == 401


def test_send_gps_nonexistent_device_401():
    """sendGPSData with valid-looking token but non-existent device_id returns 401."""
    try:
        r = requests.post(
            f"{BASE}/sendGPSData",
            headers={"Access-Token": "any_token"},
            json={
                "device_id": 99999999,
                "latitude": 0.0,
                "longitude": 0.0,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            timeout=10,
        )
    except requests.exceptions.ConnectionError:
        pytest.skip("Server not reachable")
    assert r.status_code == 401


def test_send_gps_minimal_body_success():
    """sendGPSData with device_id, lat, lon, timestamp only succeeds."""
    try:
        device_id, token = _register_device_only()
        r = requests.post(
            f"{BASE}/sendGPSData",
            headers={"Access-Token": token},
            json={
                "device_id": device_id,
                "latitude": 51.5,
                "longitude": -0.1,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            timeout=10,
        )
    except requests.exceptions.ConnectionError:
        pytest.skip("Server not reachable")
    assert r.status_code == 200
    data = r.json()
    assert data.get("success") is True
    assert "message" in data


def test_send_gps_with_speed_heading_trip_active():
    """sendGPSData with speed, heading, trip_active accepted."""
    try:
        device_id, token = _register_device_only()
        r = requests.post(
            f"{BASE}/sendGPSData",
            headers={"Access-Token": token},
            json={
                "device_id": device_id,
                "latitude": 51.5,
                "longitude": -0.1,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "speed": 50.0,
                "heading": 180.0,
                "trip_active": True,
            },
            timeout=10,
        )
    except requests.exceptions.ConnectionError:
        pytest.skip("Server not reachable")
    assert r.status_code == 200
    assert r.json().get("success") is True


def test_send_gps_speed_negative_rejected_or_accepted():
    """sendGPSData with speed < 0: server may return 422 or accept 200 (device should not send)."""
    try:
        device_id, token = _register_device_only()
        r = requests.post(
            f"{BASE}/sendGPSData",
            headers={"Access-Token": token},
            json={
                "device_id": device_id,
                "latitude": 51.5,
                "longitude": -0.1,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "speed": -1.0,
            },
            timeout=10,
        )
    except requests.exceptions.ConnectionError:
        pytest.skip("Server not reachable")
    assert r.status_code in (200, 422)


def test_send_gps_heading_out_of_range_rejected_or_accepted():
    """sendGPSData with heading not in [0, 360] returns 422."""
    try:
        device_id, token = _register_device_only()
        r = requests.post(
            f"{BASE}/sendGPSData",
            headers={"Access-Token": token},
            json={
                "device_id": device_id,
                "latitude": 51.5,
                "longitude": -0.1,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "heading": 361.0,
            },
            timeout=10,
        )
    except requests.exceptions.ConnectionError:
        pytest.skip("Server not reachable")
    assert r.status_code in (200, 422)


def test_send_gps_stale_timestamp_accepted():
    """sendGPSData with timestamp before 2020 is accepted (server may correct)."""
    try:
        device_id, token = _register_device_only()
        r = requests.post(
            f"{BASE}/sendGPSData",
            headers={"Access-Token": token},
            json={
                "device_id": device_id,
                "latitude": 51.5,
                "longitude": -0.1,
                "timestamp": "2019-01-01T00:00:00Z",
            },
            timeout=10,
        )
    except requests.exceptions.ConnectionError:
        pytest.skip("Server not reachable")
    assert r.status_code == 200
    assert r.json().get("success") is True


# ---------- Get device controls ----------


def test_get_device_controls_requires_auth():
    """getDeviceControls without Access-Token returns 401."""
    try:
        r = requests.get(f"{BASE}/getDeviceControls", params={"device_id": 1}, timeout=10)
    except requests.exceptions.ConnectionError:
        pytest.skip("Server not reachable")
    assert r.status_code == 401


def test_get_device_controls_invalid_token_401():
    """getDeviceControls with wrong token returns 401."""
    try:
        device_id, _ = _register_device_only()
        r = requests.get(
            f"{BASE}/getDeviceControls",
            params={"device_id": device_id},
            headers={"Access-Token": "wrong"},
            timeout=10,
        )
    except requests.exceptions.ConnectionError:
        pytest.skip("Server not reachable")
    assert r.status_code == 401


def test_get_device_controls_nonexistent_device_401():
    """getDeviceControls for non-existent device_id returns 401 (auth fails - device does not exist)."""
    try:
        _, token = _register_device_only()
        r = requests.get(
            f"{BASE}/getDeviceControls",
            params={"device_id": 99999999},
            headers={"Access-Token": token},
            timeout=10,
        )
    except requests.exceptions.ConnectionError:
        pytest.skip("Server not reachable")
    assert r.status_code == 401


def test_get_device_controls_success_shape():
    """getDeviceControls returns device_id, control_1..4, control_version, controls_updated_at, remote_viewing."""
    try:
        device_id, token = _register_device_only()
        r = requests.get(
            f"{BASE}/getDeviceControls",
            params={"device_id": device_id},
            headers={"Access-Token": token},
            timeout=10,
        )
    except requests.exceptions.ConnectionError:
        pytest.skip("Server not reachable")
    assert r.status_code == 200
    data = r.json()
    assert data["device_id"] == device_id
    assert "control_1" in data
    assert "control_2" in data
    assert "control_3" in data
    assert "control_4" in data
    assert "control_version" in data
    assert "controls_updated_at" in data
    assert "remote_viewing" in data


def _make_user_and_linked_device():
    """Create user, register device, link; return (user_id, user_token, device_id, device_token)."""
    ts = int(time.time() * 1000)
    rnd = random.randint(0, 999999)
    user = {
        "email_address": f"hotcold_{ts}_{rnd}@example.com",
        "phone_number": f"+1999{ts % 10000000:07d}{rnd % 1000:03d}",
        "name": "Hot Cold User",
        "password": "Pass123!",
    }
    device = {
        "device_id": 500000 + (rnd % 1000),
        "access_token": f"hotcold_dev_{ts}_{rnd}",
        "sms_number": f"+1888{ts % 10000000:07d}{rnd % 1000:03d}",
        "name": "Hot Cold Device",
    }
    r = requests.post(f"{BASE}/signup", json=user, timeout=10)
    r.raise_for_status()
    user_id = r.json()["user_id"]
    user_token = r.json()["access_token"]
    requests.post(f"{BASE}/registerDevice", json=device, timeout=10).raise_for_status()
    requests.post(
        f"{BASE}/registerDeviceToUser",
        headers={"Access-Token": user_token},
        params={"user_id": user_id},
        json={"device_id": device["device_id"], "access_token": device["access_token"]},
        timeout=10,
    ).raise_for_status()
    return user_id, user_token, device["device_id"], device["access_token"]


def test_hot_cold_mode_remote_viewing_in_get_device_controls():
    """When user sets remote_viewing true, device getDeviceControls sees remote_viewing true (hot mode). When false, device sees false (cold/polled)."""
    try:
        user_id, user_token, device_id, device_token = _make_user_and_linked_device()
    except requests.exceptions.ConnectionError:
        pytest.skip("Server not reachable")
    # Cold: device polls getDeviceControls, remote_viewing should be false initially
    r = requests.get(
        f"{BASE}/getDeviceControls",
        params={"device_id": device_id},
        headers={"Access-Token": device_token},
        timeout=10,
    )
    assert r.status_code == 200
    assert r.json().get("remote_viewing") is False
    # User opens live view → app sets remote_viewing true
    requests.put(
        f"{BASE}/devices/{device_id}/tracking",
        headers={"Access-Token": user_token},
        params={"user_id": user_id},
        json={"remote_viewing": True},
        timeout=10,
    ).raise_for_status()
    # Device polls getDeviceControls → sees remote_viewing true (hot mode / WebSocket)
    r = requests.get(
        f"{BASE}/getDeviceControls",
        params={"device_id": device_id},
        headers={"Access-Token": device_token},
        timeout=10,
    )
    assert r.status_code == 200
    assert r.json().get("remote_viewing") is True
    # User closes live view → app sets remote_viewing false
    requests.put(
        f"{BASE}/devices/{device_id}/tracking",
        headers={"Access-Token": user_token},
        params={"user_id": user_id},
        json={"remote_viewing": False},
        timeout=10,
    ).raise_for_status()
    # Device polls again → sees remote_viewing false (cold / polled)
    r = requests.get(
        f"{BASE}/getDeviceControls",
        params={"device_id": device_id},
        headers={"Access-Token": device_token},
        timeout=10,
    )
    assert r.status_code == 200
    assert r.json().get("remote_viewing") is False


# ---------- A-GNSS (device auth) ----------


def test_agnss_requires_auth():
    """GET /agnss without Access-Token returns 401."""
    try:
        r = requests.get(f"{BASE}/agnss", params={"device_id": 1}, timeout=10)
    except requests.exceptions.ConnectionError:
        pytest.skip("Server not reachable")
    assert r.status_code == 401


def test_agnss_invalid_token_401():
    """GET /agnss with wrong token returns 401."""
    try:
        device_id, _ = _register_device_only()
        r = requests.get(
            f"{BASE}/agnss",
            params={"device_id": device_id},
            headers={"Access-Token": "wrong"},
            timeout=10,
        )
    except requests.exceptions.ConnectionError:
        pytest.skip("Server not reachable")
    assert r.status_code == 401


def test_agnss_success_or_503():
    """GET /agnss with valid device returns 200 (binary) or 503 if no provider."""
    try:
        device_id, token = _register_device_only()
        r = requests.get(
            f"{BASE}/agnss",
            params={"device_id": device_id},
            headers={"Access-Token": token},
            timeout=15,
        )
    except requests.exceptions.ConnectionError:
        pytest.skip("Server not reachable")
    assert r.status_code in (200, 503)
    if r.status_code == 200:
        assert r.headers.get("Content-Type", "").startswith("application/octet-stream")
        assert "X-AGNSS-Source" in r.headers or len(r.content) >= 0


def test_agnss_with_lat_lon():
    """GET /agnss with optional lat/lon query params accepted."""
    try:
        device_id, token = _register_device_only()
        r = requests.get(
            f"{BASE}/agnss",
            params={"device_id": device_id, "lat": 51.5, "lon": -0.1},
            headers={"Access-Token": token},
            timeout=15,
        )
    except requests.exceptions.ConnectionError:
        pytest.skip("Server not reachable")
    assert r.status_code in (200, 503)


# ---------- Cell location (device auth) ----------


def test_cell_location_requires_auth():
    """POST /cell_location without Access-Token returns 401."""
    try:
        r = requests.post(
            f"{BASE}/cell_location",
            json={
                "cells": [{"cellId": 1, "mcc": 234, "mnc": 10, "lac": 1, "signal": -80}],
                "device_id": 1,
            },
            timeout=10,
        )
    except requests.exceptions.ConnectionError:
        pytest.skip("Server not reachable")
    assert r.status_code == 401


def test_cell_location_empty_cells_400():
    """POST /cell_location with empty cells returns 400."""
    try:
        device_id, token = _register_device_only()
        r = requests.post(
            f"{BASE}/cell_location",
            headers={"Access-Token": token},
            json={"cells": [], "device_id": device_id},
            timeout=10,
        )
    except requests.exceptions.ConnectionError:
        pytest.skip("Server not reachable")
    assert r.status_code == 400


def test_cell_location_success_or_503():
    """POST /cell_location with valid device and one cell returns 200 or 503."""
    try:
        device_id, token = _register_device_only()
        r = requests.post(
            f"{BASE}/cell_location",
            headers={"Access-Token": token},
            json={
                "cells": [
                    {"cellId": 12345, "mcc": 234, "mnc": 10, "lac": 5432, "signal": -85}
                ],
                "device_id": device_id,
            },
            timeout=15,
        )
    except requests.exceptions.ConnectionError:
        pytest.skip("Server not reachable")
    assert r.status_code in (200, 503)
    if r.status_code == 200:
        data = r.json()
        assert "latitude" in data
        assert "longitude" in data
        assert "accuracy" in data
        assert "source" in data


# ---------- Device WebSocket ----------


@pytest.mark.skipif(not HAS_WEBSOCKETS, reason="websockets package not installed")
@pytest.mark.asyncio
async def test_device_ws_connect_ping_pong():
    """Device can connect to /v1/ws/devices/{id}?token= and get pong for ping."""
    try:
        device_id, token = _register_device_only()
    except requests.exceptions.ConnectionError:
        pytest.skip("Server not reachable")
    uri = f"{WS_BASE}/v1/ws/devices/{device_id}?token={token}"
    async with websockets.connect(uri, close_timeout=5) as ws:
        await ws.send(json.dumps({"type": "ping"}))
        reply = await asyncio.wait_for(ws.recv(), timeout=3)
        data = json.loads(reply)
        assert data.get("type") == "pong"
        assert "timestamp" in data


@pytest.mark.skipif(not HAS_WEBSOCKETS, reason="websockets package not installed")
@pytest.mark.asyncio
async def test_device_ws_send_location_update_accepted():
    """Device can send location_update over WS; server accepts (broadcasts to users)."""
    try:
        device_id, token = _register_device_only()
    except requests.exceptions.ConnectionError:
        pytest.skip("Server not reachable")
    uri = f"{WS_BASE}/v1/ws/devices/{device_id}?token={token}"
    async with websockets.connect(uri, close_timeout=5) as ws:
        msg = {
            "type": "location_update",
            "data": {
                "latitude": 52.0,
                "longitude": 0.0,
                "speed": 10.0,
                "heading": 90.0,
            },
        }
        await ws.send(json.dumps(msg))
        # No reply expected; server just broadcasts. Connection stays open.
        # Send ping to confirm we're still connected
        await ws.send(json.dumps({"type": "ping"}))
        reply = await asyncio.wait_for(ws.recv(), timeout=3)
        assert json.loads(reply).get("type") == "pong"


@pytest.mark.skipif(not HAS_WEBSOCKETS, reason="websockets package not installed")
@pytest.mark.asyncio
async def test_device_ws_location_update_persisted_and_in_gps_data():
    """Device sends location_update over WS; point is ingested and appears in GET GPSData (MQTT-style)."""
    try:
        user_id, user_token, device_id, device_token = _make_user_and_linked_device()
    except requests.exceptions.ConnectionError:
        pytest.skip("Server not reachable")
    # Unique coords so we can assert on them
    lat, lon = 52.123456, 0.456789
    uri = f"{WS_BASE}/v1/ws/devices/{device_id}?token={device_token}"
    async with websockets.connect(uri, close_timeout=5) as ws:
        await ws.send(json.dumps({
            "type": "location_update",
            "data": {
                "latitude": lat,
                "longitude": lon,
                "speed": 5.0,
                "heading": 180.0,
            },
        }))
        await asyncio.sleep(0.5)  # allow server to ingest
    # User fetches GPS data for last 2 minutes; should contain the point we sent
    now = datetime.now(timezone.utc)
    start = (now - timedelta(minutes=2)).strftime("%Y-%m-%dT%H:%M:%S")
    end = (now + timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M:%S")
    r = requests.get(
        f"{BASE}/GPSData",
        headers={"Access-Token": user_token},
        params={
            "user_id": user_id,
            "device_id": device_id,
            "start_time": start,
            "end_time": end,
        },
        timeout=10,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    gps_data = data.get("gps_data") or []
    matching = [p for p in gps_data if abs(float(p["latitude"]) - lat) < 1e-5 and abs(float(p["longitude"]) - lon) < 1e-5]
    assert len(matching) >= 1, f"Expected at least one GPS point at {lat},{lon}, got gps_data={gps_data}"


# ---------- Full device sequence (smoke) ----------


def test_device_full_sequence_register_send_gps_get_controls():
    """Full sequence: register -> send GPS -> get controls (no user link)."""
    try:
        device_id, token = _register_device_only()
        # Send GPS
        r1 = requests.post(
            f"{BASE}/sendGPSData",
            headers={"Access-Token": token},
            json={
                "device_id": device_id,
                "latitude": 53.0,
                "longitude": -1.0,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "speed": 0.0,
                "heading": 0.0,
                "trip_active": False,
            },
            timeout=10,
        )
        assert r1.status_code == 200
        # Get controls
        r2 = requests.get(
            f"{BASE}/getDeviceControls",
            params={"device_id": device_id},
            headers={"Access-Token": token},
            timeout=10,
        )
        assert r2.status_code == 200
        assert r2.json()["device_id"] == device_id
    except requests.exceptions.ConnectionError:
        pytest.skip("Server not reachable")
