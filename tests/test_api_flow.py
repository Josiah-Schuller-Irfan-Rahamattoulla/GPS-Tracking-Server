import os
import time
from datetime import datetime, timezone

import pytest
import requests


def _base_url() -> str:
    return os.getenv("TEST_BASE_URL", "http://localhost:8000")


@pytest.fixture(scope="module")
def test_entities():
    ts = int(time.time())
    user = {
        "email_address": f"ci_user_{ts}@example.com",
        "phone_number": f"+1555{ts % 10000000:07d}",
        "name": "CI Test User",
        "password": "TestPass123!",
    }
    device = {
        "device_id": ts % 1000000,
        "access_token": f"ci_token_{ts}",
        "sms_number": f"+1666{ts % 10000000:07d}",
        "name": "CI Test Device",
    }
    return user, device


def test_signup_login_register_flow(test_entities):
    base = _base_url()
    user, device = test_entities

    try:
        signup = requests.post(f"{base}/v1/signup", json=user, timeout=10)
    except requests.exceptions.ConnectionError:
        pytest.skip("Server not reachable")

    signup.raise_for_status()
    user_data = signup.json()
    assert user_data.get("access_token")
    user_id = user_data.get("user_id")
    access_token = user_data.get("access_token")

    login = requests.post(
        f"{base}/v1/login",
        json={"email_address": user["email_address"], "password": user["password"]},
        timeout=10,
    )
    login.raise_for_status()
    assert login.json().get("access_token")

    register = requests.post(f"{base}/v1/registerDevice", json=device, timeout=10)
    register.raise_for_status()

    link = requests.post(
        f"{base}/v1/registerDeviceToUser",
        headers={"Access-Token": access_token},
        params={"user_id": user_id},
        json={"device_id": device["device_id"]},
        timeout=10,
    )
    link.raise_for_status()

    gps_data = {
        "device_id": device["device_id"],
        "latitude": 37.7749,
        "longitude": -122.4194,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "speed": 12.3,
        "heading": 45.0,
        "trip_active": False,
    }
    send = requests.post(
        f"{base}/v1/sendGPSData",
        headers={"Access-Token": device["access_token"]},
        json=gps_data,
        timeout=10,
    )
    send.raise_for_status()
