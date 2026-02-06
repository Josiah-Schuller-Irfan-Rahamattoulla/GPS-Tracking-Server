"""
Test script for geofence breach detection functionality.
Run this after starting Docker containers to verify the implementation.
"""
import requests
import time
from datetime import datetime, timezone

BASE_URL = "http://localhost:8000"

# Test data
TEST_USER = {
    "email_address": f"test_geo_{int(time.time())}@example.com",
    "phone_number": f"+1555{int(time.time()) % 10000000:07d}",
    "name": "Geofence Test User",
    "password": "TestPass123!"
}

TEST_DEVICE = {
    "device_id": int(time.time()) % 1000000,
    "access_token": f"dev_token_{int(time.time())}",
    "sms_number": f"+1666{int(time.time()) % 10000000:07d}",
    "name": "Test GPS Device"
}

# Home location (example: San Francisco)
HOME_LAT = 37.7749
HOME_LON = -122.4194

# Away location (1km away from home)
AWAY_LAT = 37.7840
AWAY_LON = -122.4094

def test_geofence_breach_detection():
    """Test complete geofence breach detection flow."""
    
    print("\n=== Testing Geofence Breach Detection ===\n")
    
    # 1. Sign up user
    print("1. Creating test user...")
    response = requests.post(f"{BASE_URL}/v1/signup", json=TEST_USER)
    assert response.status_code == 200, f"Signup failed: {response.text}"
    user_data = response.json()
    access_token = user_data["access_token"]
    print(f"   ✓ User created with access_token: {access_token[:20]}...")
    
    # 2. Register device
    print("\n2. Registering test device...")
    response = requests.post(f"{BASE_URL}/registerDevice", json=TEST_DEVICE)
    assert response.status_code == 200, f"Device registration failed: {response.text}"
    print(f"   ✓ Device {TEST_DEVICE['device_id']} registered")
    
    # 3. Link device to user
    print("\n3. Linking device to user...")
    response = requests.post(
        f"{BASE_URL}/linkDeviceToUser",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"device_id": TEST_DEVICE['device_id']}
    )
    assert response.status_code == 200, f"Device linking failed: {response.text}"
    print(f"   ✓ Device linked to user")
    
    # 4. Create geofence around home
    print("\n4. Creating geofence around 'home' location...")
    geofence_data = {
        "name": "Home Zone",
        "latitude": HOME_LAT,
        "longitude": HOME_LON,
        "radius": 200.0,  # 200 meters
        "enabled": True
    }
    response = requests.post(
        f"{BASE_URL}/geofences",
        headers={"Authorization": f"Bearer {access_token}"},
        json=geofence_data
    )
    assert response.status_code == 200, f"Geofence creation failed: {response.text}"
    geofence = response.json()
    print(f"   ✓ Geofence created: ID={geofence['geofence_id']}, radius={geofence['radius']}m")
    
    # 5. Send GPS data - Device INSIDE geofence
    print("\n5. Sending GPS data INSIDE geofence...")
    gps_data = {
        "device_id": TEST_DEVICE['device_id'],
        "latitude": HOME_LAT + 0.0001,  # ~11 meters north
        "longitude": HOME_LON + 0.0001,  # ~11 meters east
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "speed": 0.0,
        "heading": 0.0,
        "trip_active": False
    }
    response = requests.post(f"{BASE_URL}/sendGPSData", json=gps_data)
    assert response.status_code == 200, f"GPS data failed: {response.text}"
    print(f"   ✓ GPS data sent (inside geofence)")
    time.sleep(1)
    
    # 6. Check for ENTERED event
    print("\n6. Checking for geofence ENTERED event...")
    response = requests.get(
        f"{BASE_URL}/geofence-breach-events",
        headers={"Authorization": f"Bearer {access_token}"},
        params={"limit": 10}
    )
    assert response.status_code == 200, f"Failed to fetch events: {response.text}"
    events = response.json()
    entered_events = [e for e in events if e['event_type'] == 'ENTERED']
    assert len(entered_events) > 0, "No ENTERED event found!"
    print(f"   ✓ ENTERED event detected: {entered_events[0]['event_id']}")
    
    # 7. Send GPS data - Device OUTSIDE geofence
    print("\n7. Sending GPS data OUTSIDE geofence...")
    gps_data = {
        "device_id": TEST_DEVICE['device_id'],
        "latitude": AWAY_LAT,
        "longitude": AWAY_LON,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "speed": 50.0,
        "heading": 180.0,
        "trip_active": True
    }
    response = requests.post(f"{BASE_URL}/sendGPSData", json=gps_data)
    assert response.status_code == 200, f"GPS data failed: {response.text}"
    print(f"   ✓ GPS data sent (outside geofence)")
    time.sleep(1)
    
    # 8. Check for EXITED event
    print("\n8. Checking for geofence EXITED event...")
    response = requests.get(
        f"{BASE_URL}/geofence-breach-events",
        headers={"Authorization": f"Bearer {access_token}"},
        params={"limit": 10}
    )
    assert response.status_code == 200, f"Failed to fetch events: {response.text}"
    events = response.json()
    exited_events = [e for e in events if e['event_type'] == 'EXITED']
    assert len(exited_events) > 0, "No EXITED event found!"
    print(f"   ✓ EXITED event detected: {exited_events[0]['event_id']}")
    
    # 9. Send GPS data - Back INSIDE geofence
    print("\n9. Sending GPS data back INSIDE geofence...")
    gps_data = {
        "device_id": TEST_DEVICE['device_id'],
        "latitude": HOME_LAT,
        "longitude": HOME_LON,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "speed": 10.0,
        "heading": 90.0,
        "trip_active": True
    }
    response = requests.post(f"{BASE_URL}/sendGPSData", json=gps_data)
    assert response.status_code == 200, f"GPS data failed: {response.text}"
    print(f"   ✓ GPS data sent (returned to geofence)")
    time.sleep(1)
    
    # 10. Verify second ENTERED event
    print("\n10. Checking for second ENTERED event...")
    response = requests.get(
        f"{BASE_URL}/geofence-breach-events",
        headers={"Authorization": f"Bearer {access_token}"},
        params={"limit": 10}
    )
    assert response.status_code == 200, f"Failed to fetch events: {response.text}"
    events = response.json()
    entered_events = [e for e in events if e['event_type'] == 'ENTERED']
    assert len(entered_events) >= 2, "Second ENTERED event not found!"
    print(f"   ✓ Second ENTERED event detected")
    
    print("\n=== ALL TESTS PASSED ===\n")
    print(f"Summary:")
    print(f"  - User: {TEST_USER['email_address']}")
    print(f"  - Device: {TEST_DEVICE['device_id']}")
    print(f"  - Geofence: ID={geofence['geofence_id']}, '{geofence['name']}'")
    print(f"  - Total breach events: {len(events)}")
    print(f"  - ENTERED events: {len([e for e in events if e['event_type'] == 'ENTERED'])}")
    print(f"  - EXITED events: {len([e for e in events if e['event_type'] == 'EXITED'])}")
    
    return {
        "user": user_data,
        "device": TEST_DEVICE,
        "geofence": geofence,
        "events": events
    }


if __name__ == "__main__":
    try:
        result = test_geofence_breach_detection()
        print("\n✅ Test completed successfully!")
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        exit(1)
    except requests.exceptions.ConnectionError:
        print("\n❌ Cannot connect to server. Is Docker running?")
        print("   Run: docker-compose up -d")
        exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
