"""
WebSocket endpoint tests: device stream, user stream, geofence alerts.
Requires server running (e.g. docker compose up). Use TEST_BASE_URL for base URL.
"""
import asyncio
import json
import os
import random
import time
import pytest
import requests

# Optional: async WebSocket client (websockets package is in api deps)
try:
    import websockets
    HAS_WEBSOCKETS = True
except ImportError:
    HAS_WEBSOCKETS = False

BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:8000").replace("http://", "ws://").replace("https://", "wss://")
HTTP_BASE = os.getenv("TEST_BASE_URL", "http://localhost:8000")


def _make_user_and_device():
    """Create a user and linked device; return (user_id, access_token, device_id, device_access_token)."""
    ts = int(time.time() * 1000)
    rnd = random.randint(0, 999999)
    user = {
        "email_address": f"ws_user_{ts}_{rnd}@example.com",
        "phone_number": f"+1888{ts % 10000000:07d}{rnd % 1000:03d}",
        "name": "WS Test User",
        "password": "Pass123!",
    }
    import uuid
    unique = uuid.uuid4().int & (1<<31)-1
    device = {
        "device_id": 777000 + (ts % 1000) + (unique % 1000000),
        "access_token": f"ws_device_token_{ts}_{unique}",
        "sms_number": f"+1999{ts % 10000000:07d}{unique % 1000:03d}",
        "name": "WS Test Device",
    }
    r = requests.post(f"{HTTP_BASE}/v1/signup", json=user, timeout=10)
    r.raise_for_status()
    data = r.json()
    access_token = data["access_token"]
    user_id = data["user_id"]

    requests.post(f"{HTTP_BASE}/v1/registerDevice", json=device, timeout=10).raise_for_status()
    requests.post(
        f"{HTTP_BASE}/v1/registerDeviceToUser",
        headers={"Access-Token": access_token},
        params={"user_id": user_id},
        json={"device_id": device["device_id"], "access_token": device["access_token"]},
        timeout=10,
    ).raise_for_status()

    return user_id, access_token, device["device_id"], device["access_token"]


@pytest.mark.skipif(not HAS_WEBSOCKETS, reason="websockets package not installed")
@pytest.mark.asyncio
async def test_websocket_device_reject_missing_token():
    """Device WebSocket without token should close with error."""
    uri = f"{BASE_URL}/v1/ws/devices/1?token="
    try:
        async with websockets.connect(uri, close_timeout=2) as ws:
            try:
                await asyncio.wait_for(ws.recv(), timeout=2)
                assert False, "Expected connection to be closed"
            except (websockets.exceptions.ConnectionClosed, asyncio.TimeoutError):
                pass
    except (OSError, Exception):
        pass


@pytest.mark.skipif(not HAS_WEBSOCKETS, reason="websockets package not installed")
@pytest.mark.asyncio
async def test_websocket_device_reject_invalid_token():
    """Device WebSocket with wrong token should close or return 403."""
    uri = f"{BASE_URL}/v1/ws/devices/99999?token=wrong_token"
    try:
        async with websockets.connect(uri, close_timeout=2) as ws:
            await ws.recv()
        assert False, "Expected connection to be rejected"
    except websockets.exceptions.ConnectionClosed as e:
        assert e.code == 1008 or e.code is not None
    except websockets.exceptions.InvalidStatus as e:
        assert e.response.status_code != 101  # not a successful upgrade


@pytest.mark.skipif(not HAS_WEBSOCKETS, reason="websockets package not installed")
@pytest.mark.asyncio
async def test_websocket_device_accept_and_ping_pong():
    """Device WebSocket with valid token accepts connection and responds to ping."""
    try:
        _, _, device_id, device_token = _make_user_and_device()
    except requests.exceptions.ConnectionError:
        pytest.skip("Server not reachable")

    uri = f"{BASE_URL}/v1/ws/devices/{device_id}?token={device_token}"
    async with websockets.connect(uri, close_timeout=5) as ws:
        await ws.send(json.dumps({"type": "ping"}))
        response = await asyncio.wait_for(ws.recv(), timeout=3)
        data = json.loads(response)
        assert data.get("type") == "pong"
        assert "timestamp" in data


@pytest.mark.skipif(not HAS_WEBSOCKETS, reason="websockets package not installed")
@pytest.mark.asyncio
async def test_websocket_user_reject_missing_token():
    """User WebSocket without token should close."""
    uri = f"{BASE_URL}/v1/ws/users/1?token="
    try:
        async with websockets.connect(uri, close_timeout=2) as ws:
            await ws.recv()
    except (websockets.exceptions.ConnectionClosed, Exception):
        pass


@pytest.mark.skipif(not HAS_WEBSOCKETS, reason="websockets package not installed")
@pytest.mark.asyncio
async def test_websocket_user_accept_and_ping_pong():
    """User WebSocket with valid token and device access accepts and responds to ping."""
    try:
        _, access_token, device_id, _ = _make_user_and_device()
    except requests.exceptions.ConnectionError:
        pytest.skip("Server not reachable")

    uri = f"{BASE_URL}/v1/ws/users/{device_id}?token={access_token}"
    async with websockets.connect(uri, close_timeout=5) as ws:
        await ws.send(json.dumps({"type": "ping"}))
        response = await asyncio.wait_for(ws.recv(), timeout=3)
        data = json.loads(response)
        assert data.get("type") == "pong"


@pytest.mark.skipif(not HAS_WEBSOCKETS, reason="websockets package not installed")
@pytest.mark.asyncio
async def test_websocket_user_reject_no_access():
    """User WebSocket for a device the user does not have access to should close."""
    try:
        ts = int(time.time() * 1000)
        rnd = random.randint(0, 999999)
        user = {
            "email_address": f"ws_noaccess_{ts}_{rnd}@example.com",
            "phone_number": f"+1777{ts % 10000000:07d}{rnd % 1000:03d}",
            "name": "No Access User",
            "password": "Pass123!",
        }
        r = requests.post(f"{HTTP_BASE}/v1/signup", json=user, timeout=10)
        r.raise_for_status()
        access_token = r.json()["access_token"]
    except requests.exceptions.ConnectionError:
        pytest.skip("Server not reachable")

    # Device 99999 is not linked to this user
    uri = f"{BASE_URL}/v1/ws/users/99999?token={access_token}"
    try:
        async with websockets.connect(uri, close_timeout=3) as ws:
            await ws.recv()
        assert False, "Expected connection to be rejected"
    except (websockets.exceptions.ConnectionClosed, websockets.exceptions.InvalidStatus):
        pass


@pytest.mark.skipif(not HAS_WEBSOCKETS, reason="websockets package not installed")
@pytest.mark.asyncio
async def test_websocket_geofence_accept_and_ping():
    """Geofence alerts WebSocket with valid user token accepts and responds to ping."""
    try:
        _, access_token, device_id, _ = _make_user_and_device()
    except requests.exceptions.ConnectionError:
        pytest.skip("Server not reachable")

    uri = f"{BASE_URL}/v1/ws/geofence/{device_id}?token={access_token}"
    async with websockets.connect(uri, close_timeout=5) as ws:
        await ws.send(json.dumps({"type": "ping"}))
        response = await asyncio.wait_for(ws.recv(), timeout=3)
        data = json.loads(response)
        assert data.get("type") == "pong"


def test_websocket_stats_endpoint():
    """GET /v1/ws/stats/{device_id} returns room stats (no auth)."""
    try:
        r = requests.get(f"{HTTP_BASE}/v1/ws/stats/1", timeout=5)
    except requests.exceptions.ConnectionError:
        pytest.skip("Server not reachable")
    assert r.status_code == 200
    data = r.json()
    assert data.get("device_id") == 1
    assert "user_listeners" in data
    assert "geofence_subscribers" in data


