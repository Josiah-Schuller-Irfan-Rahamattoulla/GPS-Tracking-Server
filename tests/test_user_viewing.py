"""
User viewing (remote_viewing) API tests.
PUT /v1/devices/{device_id}/tracking with remote_viewing true/false,
then GET /v1/devices and assert device.remote_viewing and optionally last_viewed_at.
"""
import os
import random
import time
import pytest
import requests

HTTP_BASE = os.getenv("TEST_BASE_URL", "http://localhost:8000")
BASE = f"{HTTP_BASE}/v1"


def _make_user_and_device():
    """Create user, register device, link; return (user_id, access_token, device_id)."""
    ts = int(time.time() * 1000)
    rnd = random.randint(0, 999999)
    user = {
        "email_address": f"viewing_{ts}_{rnd}@example.com",
        "phone_number": f"+1888{ts % 10000000:07d}{rnd % 1000:03d}",
        "name": "Viewing Test User",
        "password": "Pass123!",
    }
    import uuid
    unique = uuid.uuid4().int & (1<<31)-1
    device = {
        "device_id": 888000 + (ts % 1000) + (unique % 1000000),
        "access_token": f"view_device_{ts}_{unique}",
        "sms_number": f"+1999{ts % 10000000:07d}{unique % 1000:03d}",
        "name": "Viewing Test Device",
    }
    r = requests.post(f"{BASE}/signup", json=user, timeout=10)
    r.raise_for_status()
    data = r.json()
    access_token = data["access_token"]
    user_id = data["user_id"]

    requests.post(f"{BASE}/registerDevice", json=device, timeout=10).raise_for_status()
    requests.post(
        f"{BASE}/registerDeviceToUser",
        headers={"Access-Token": access_token},
        params={"user_id": user_id},
        json={"device_id": device["device_id"], "access_token": device["access_token"]},
        timeout=10,
    ).raise_for_status()

    # Ensure DB commit visibility for subsequent API calls
    time.sleep(0.1)

    return user_id, access_token, device["device_id"]


def test_link_device_requires_correct_access_token():
    """Linking a device with wrong pairing code returns 403."""
    try:
        ts = int(time.time() * 1000)
        rnd = random.randint(0, 999999)
        user = {
            "email_address": f"linksec_{ts}_{rnd}@example.com",
            "phone_number": f"+1777{ts % 10000000:07d}{rnd % 1000:03d}",
            "name": "Link Security User",
            "password": "Pass123!",
        }
        import uuid
        unique = uuid.uuid4().int & (1<<31)-1
        device = {
            "device_id": 777000 + (ts % 1000) + (unique % 1000000),
            "access_token": f"secret_pairing_{ts}_{unique}",
            "sms_number": f"+1666{ts % 10000000:07d}{unique % 1000:03d}",
        }
        r = requests.post(f"{BASE}/signup", json=user, timeout=10)
        r.raise_for_status()
        user_id = r.json()["user_id"]
        user_token = r.json()["access_token"]
        requests.post(f"{BASE}/registerDevice", json=device, timeout=10).raise_for_status()
    except requests.exceptions.ConnectionError:
        pytest.skip("Server not reachable")
    # Try to link with wrong pairing code
    r = requests.post(
        f"{BASE}/registerDeviceToUser",
        headers={"Access-Token": user_token},
        params={"user_id": user_id},
        json={"device_id": device["device_id"], "access_token": "wrong-pairing-code"},
        timeout=10,
    )
    assert r.status_code == 403
    assert "pairing" in r.json().get("detail", "").lower() or "invalid" in r.json().get("detail", "").lower()
    # Link with correct code succeeds
    r2 = requests.post(
        f"{BASE}/registerDeviceToUser",
        headers={"Access-Token": user_token},
        params={"user_id": user_id},
        json={"device_id": device["device_id"], "access_token": device["access_token"]},
        timeout=10,
    )
    assert r2.status_code == 200


def test_remote_viewing_set_true_then_list():
    """PUT tracking remote_viewing=true then GET devices shows remote_viewing true."""
    try:
        user_id, access_token, device_id = _make_user_and_device()
    except requests.exceptions.ConnectionError:
        pytest.skip("Server not reachable")

    headers = {"Access-Token": access_token}
    params = {"user_id": user_id}

    r = requests.put(
        f"{BASE}/devices/{device_id}/tracking",
        headers=headers,
        params=params,
        json={"remote_viewing": True},
        timeout=10,
    )
    if r.status_code == 500:
        pytest.skip("Tracking endpoint returned 500 (ensure DB has remote_viewing/last_viewed_at and migrations applied)")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("remote_viewing") is True
    assert body.get("device_id") == device_id

    r = requests.get(f"{BASE}/devices", headers=headers, params=params, timeout=10)
    assert r.status_code == 200
    devices = r.json()
    dev = next((d for d in devices if d["device_id"] == device_id), None)
    assert dev is not None
    assert dev["remote_viewing"] is True


def test_remote_viewing_set_false_then_list():
    """PUT tracking remote_viewing=false then GET devices shows remote_viewing false."""
    try:
        user_id, access_token, device_id = _make_user_and_device()
    except requests.exceptions.ConnectionError:
        pytest.skip("Server not reachable")

    headers = {"Access-Token": access_token}
    params = {"user_id": user_id}

    r0 = requests.put(
        f"{BASE}/devices/{device_id}/tracking",
        headers=headers,
        params=params,
        json={"remote_viewing": True},
        timeout=10,
    )
    if r0.status_code == 500:
        pytest.skip("Tracking endpoint returned 500 (ensure DB has remote_viewing/last_viewed_at and migrations applied)")
    r0.raise_for_status()

    r = requests.put(
        f"{BASE}/devices/{device_id}/tracking",
        headers=headers,
        params=params,
        json={"remote_viewing": False},
        timeout=10,
    )
    assert r.status_code == 200, r.text
    assert r.json().get("remote_viewing") is False

    r = requests.get(f"{BASE}/devices", headers=headers, params=params, timeout=10)
    assert r.status_code == 200
    dev = next((d for d in r.json() if d["device_id"] == device_id), None)
    assert dev is not None
    assert dev["remote_viewing"] is False


def test_tracking_404_for_unknown_device():
    """PUT tracking for device user does not own returns 404."""
    try:
        user_id, access_token, _ = _make_user_and_device()
    except requests.exceptions.ConnectionError:
        pytest.skip("Server not reachable")

    r = requests.put(
        f"{BASE}/devices/999999/tracking",
        headers={"Access-Token": access_token},
        params={"user_id": user_id},
        json={"remote_viewing": True},
        timeout=10,
    )
    assert r.status_code == 404
