"""
Baseline test suite to lock down current API behavior.
Run with: pytest tests/test_baseline.py
"""
import requests
import pytest

BASE_URL = "http://localhost:8000/v1"

# Test user credentials
TEST_USER = {
    "email": f"baseline_test_{int(__import__('time').time())}@example.com",
    "password": "SecurePass123!",
    "sms_number": "+1234567890"
}

TEST_DEVICE = {
    "device_id": f"999{int(__import__('time').time()) % 100000}",
    "sms_number": "+1234567890"
}


@pytest.fixture(scope="module")
def auth_token():
    """Create a test user and return auth token."""
    response = requests.post(f"{BASE_URL}/signup", json=TEST_USER)
    assert response.status_code == 200, f"Signup failed: {response.text}"
    data = response.json()
    return data["access_token"], data["user_id"]


@pytest.fixture(scope="module")
def test_device(auth_token):
    """Register and link a test device."""
    access_token, user_id = auth_token
    
    # Register device
    response = requests.post(f"{BASE_URL}/registerDevice", json=TEST_DEVICE)
    assert response.status_code == 200, f"Device registration failed: {response.text}"
    
    # Link device to user
    response = requests.post(
        f"{BASE_URL}/registerDeviceToUser",
        headers={"Access-Token": access_token},
        params={"user_id": user_id},
        json={"device_id": TEST_DEVICE["device_id"]}
    )
    assert response.status_code == 200, f"Device linking failed: {response.text}"
    
    return TEST_DEVICE["device_id"]


def test_user_signup():
    """Test user signup endpoint."""
    user_data = {
        "email": f"signup_test_{int(__import__('time').time())}@example.com",
        "password": "TestPass123!",
        "sms_number": "+9876543210"
    }
    response = requests.post(f"{BASE_URL}/signup", json=user_data)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "user_id" in data
    assert data["email"] == user_data["email"]


def test_device_registration():
    """Test device registration endpoint."""
    device_data = {
        "device_id": f"888{int(__import__('time').time()) % 100000}",
        "sms_number": "+1111111111"
    }
    response = requests.post(f"{BASE_URL}/registerDevice", json=device_data)
    assert response.status_code == 200
    data = response.json()
    assert data["device_id"] == device_data["device_id"]


def test_gps_data_ingestion(auth_token, test_device):
    """Test GPS data endpoint."""
    access_token, user_id = auth_token
    
    gps_data = {
        "device_id": test_device,
        "latitude": 37.7749,
        "longitude": -122.4194,
        "speed": 25.5,
        "altitude": 10.0,
        "timestamp": "2026-02-06T12:00:00Z"
    }
    
    response = requests.post(f"{BASE_URL}/sendGPSData", json=gps_data)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"


def test_geofence_creation(auth_token):
    """Test geofence creation endpoint."""
    access_token, user_id = auth_token
    
    geofence_data = {
        "name": "Test Geofence",
        "latitude": 37.7749,
        "longitude": -122.4194,
        "radius": 500.0,
        "enabled": True
    }
    
    response = requests.post(
        f"{BASE_URL}/geofences",
        headers={"Access-Token": access_token},
        params={"user_id": user_id},
        json=geofence_data
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == geofence_data["name"]
    assert "geofence_id" in data


def test_geofence_breach_detection(auth_token, test_device):
    """Test server-side geofence breach detection."""
    access_token, user_id = auth_token
    
    # Create geofence
    geofence_data = {
        "name": "Breach Test Zone",
        "latitude": 37.7749,
        "longitude": -122.4194,
        "radius": 200.0,
        "enabled": True
    }
    
    response = requests.post(
        f"{BASE_URL}/geofences",
        headers={"Access-Token": access_token},
        params={"user_id": user_id},
        json=geofence_data
    )
    assert response.status_code == 200
    geofence_id = response.json()["geofence_id"]
    
    # Send GPS inside geofence
    gps_data = {
        "device_id": test_device,
        "latitude": 37.7749,  # Inside
        "longitude": -122.4194,
        "speed": 0.0,
        "altitude": 10.0,
        "timestamp": "2026-02-06T12:00:00Z"
    }
    
    response = requests.post(f"{BASE_URL}/sendGPSData", json=gps_data)
    assert response.status_code == 200
    
    # Check for breach events
    response = requests.get(
        f"{BASE_URL}/geofence-breach-events",
        headers={"Access-Token": access_token},
        params={"user_id": user_id}
    )
    assert response.status_code == 200
    events = response.json()
    assert len(events) > 0
    assert any(e["breach_type"] == "ENTERED" for e in events)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
