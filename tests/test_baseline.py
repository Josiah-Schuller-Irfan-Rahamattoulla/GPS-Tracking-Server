"""
Baseline test suite to lock down current API behavior.
Run with: pytest tests/test_baseline.py
"""
import time
import random
import requests
import pytest
from datetime import datetime, timezone
import os

BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:8000") + "/v1"

def _unique_user():
    """Unique user payload to avoid duplicate key errors across runs."""
    ts = int(time.time())
    rnd = random.randint(0, 999999)
    return {
        "email_address": f"baseline_test_{ts}_{rnd}@example.com",
        "phone_number": f"+1555{ts % 10000000:07d}{rnd % 1000:03d}",
        "name": "Baseline Test User",
        "password": "SecurePass123!",
    }


def _unique_device():
    """Unique device payload (device_id int, access_token, sms_number, name)."""
    import uuid
    unique = uuid.uuid4().int & (1<<31)-1
    ts = int(time.time())
    return {
        "device_id": 999000 + (ts % 1000) + (unique % 1000000),
        "access_token": f"baseline_token_{ts}_{unique}",
        "sms_number": f"+1666{ts % 10000000:07d}{unique % 1000:03d}",
        "name": "Baseline Test Device",
    }


@pytest.fixture(scope="module")
def auth_token():
    """Create a test user and return auth token and user_id."""
    user = _unique_user()
    response = requests.post(f"{BASE_URL}/signup", json=user, timeout=10)
    assert response.status_code == 200, f"Signup failed: {response.text}"
    data = response.json()
    return data["access_token"], data["user_id"]


@pytest.fixture(scope="module")
def test_device(auth_token):
    """Register and link a test device. Returns (device_id, device_access_token)."""
    access_token, user_id = auth_token
    device = _unique_device()

    # Register device
    response = requests.post(f"{BASE_URL}/registerDevice", json=device, timeout=10)
    assert response.status_code == 200, f"Device registration failed: {response.text}"

    # Link device to user (access_token proves ownership)
    response = requests.post(
        f"{BASE_URL}/registerDeviceToUser",
        headers={"Access-Token": access_token},
        params={"user_id": user_id},
        json={"device_id": device["device_id"], "access_token": device["access_token"]},
        timeout=10,
    )
    assert response.status_code == 200, f"Device linking failed: {response.text}"

    return device["device_id"], device["access_token"]


def test_user_signup():
    """Test user signup endpoint."""
    ts = int(time.time())
    user_data = {
        "email_address": f"signup_test_{ts}@example.com",
        "phone_number": f"+1999{ts % 10000000:07d}",
        "name": "Signup Test User",
        "password": "TestPass123!",
    }
    response = requests.post(f"{BASE_URL}/signup", json=user_data, timeout=10)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "user_id" in data
    assert data["email_address"] == user_data["email_address"]


def test_device_registration():
    """Test device registration endpoint."""
    ts = int(time.time())
    device_data = {
        "device_id": 888000 + (ts % 1000),
        "access_token": f"reg_test_{ts}",
        "sms_number": f"+1777{ts % 10000000:07d}",
        "name": "Reg Test Device",
    }
    response = requests.post(f"{BASE_URL}/registerDevice", json=device_data, timeout=10)
    assert response.status_code == 200
    data = response.json()
    assert data.get("success") is True or "device_id" in data or "message" in data


def test_gps_data_ingestion(auth_token, test_device):
    """Test GPS data endpoint (device_id int, timestamp datetime, no altitude; requires device Access-Token)."""
    device_id, device_access_token = test_device

    gps_data = {
        "device_id": device_id,
        "latitude": 37.7749,
        "longitude": -122.4194,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "speed": 25.5,
        "heading": 90.0,
        "trip_active": False,
    }

    response = requests.post(
        f"{BASE_URL}/sendGPSData",
        headers={"Access-Token": device_access_token},
        json=gps_data,
        timeout=10,
    )
    assert response.status_code == 200
    data = response.json()
    assert data.get("success") is True
    assert "message" in data


def test_geofence_creation(auth_token):
    """Test geofence creation endpoint."""
    access_token, user_id = auth_token

    geofence_data = {
        "name": "Test Geofence",
        "latitude": 37.7749,
        "longitude": -122.4194,
        "radius": 500.0,
        "enabled": True,
    }

    response = requests.post(
        f"{BASE_URL}/geofences",
        headers={"Access-Token": access_token},
        params={"user_id": user_id},
        json=geofence_data,
        timeout=10,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == geofence_data["name"]
    assert "geofence_id" in data


def test_geofence_breach_detection(auth_token, test_device):
    """Test server-side geofence breach detection."""
    access_token, user_id = auth_token
    device_id, device_access_token = test_device

    # Create geofence
    geofence_data = {
        "name": "Breach Test Zone",
        "latitude": 37.7749,
        "longitude": -122.4194,
        "radius": 200.0,
        "enabled": True,
    }

    response = requests.post(
        f"{BASE_URL}/geofences",
        headers={"Access-Token": access_token},
        params={"user_id": user_id},
        json=geofence_data,
        timeout=10,
    )
    assert response.status_code == 200
    geofence_id = response.json()["geofence_id"]

    # Send GPS inside geofence (may trigger ENTERED breach depending on implementation)
    gps_data = {
        "device_id": device_id,
        "latitude": 37.7749,
        "longitude": -122.4194,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "speed": 0.0,
        "trip_active": False,
    }

    response = requests.post(
        f"{BASE_URL}/sendGPSData",
        headers={"Access-Token": device_access_token},
        json=gps_data,
        timeout=10,
    )
    assert response.status_code == 200

    # Check for breach events (list may be empty if breach only on transition)
    response = requests.get(
        f"{BASE_URL}/geofence-breach-events",
        headers={"Access-Token": access_token},
        params={"user_id": user_id},
        timeout=10,
    )
    assert response.status_code == 200
    events = response.json()
    assert isinstance(events, list)
    if len(events) > 0:
        assert any(e.get("event_type") == "ENTERED" for e in events)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
