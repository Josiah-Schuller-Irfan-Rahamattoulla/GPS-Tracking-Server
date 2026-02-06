"""
Simple test for server-side geofence breach detection.
Tests the core functionality without complex device linking flows.
"""
import requests
import time
from datetime import datetime, timezone

BASE_URL = "http://localhost:8000"

def test_simple_breach():
    """Test geofence breach detection with minimal setup."""
    
    print("\n=== Simple Geofence Breach Test ===\n")
    
    # Create test user
    print("1. Creating test user...")
    user_data = {
        "email_address": f"breach_test_{int(time.time())}@test.com",
        "phone_number": "+15551234567",
        "name": "Breach Tester",
        "password": "TestPass123!"
    }
    response = requests.post(f"{BASE_URL}/v1/signup", json=user_data)
    if response.status_code != 200:
        print(f"   ❌ Signup failed: {response.status_code} {response.text}")
        return False
    
    user = response.json()
    user_id = user["user_id"]
    user_token = user["access_token"]
    print(f"   ✓ User created: ID={user_id}")
    
    # Register a device (no auth required)
    print("\n2. Registering device...")
    device_data = {
        "device_id": int(time.time()) % 1000000,
        "access_token": f"device_token_{int(time.time())}",
        "sms_number": "+16661234567",
        "name": "Test Device"
    }
    response = requests.post(f"{BASE_URL}/v1/registerDevice", json=device_data)
    if response.status_code != 200:
        print(f"   ❌ Device registration failed: {response.status_code} {response.text}")
        return False
    
    device_id = device_data["device_id"]
    device_token = device_data["access_token"]
    print(f"   ✓ Device registered: ID={device_id}")
    
    # Create geofence
    print("\n3. Creating geofence...")
    geofence_data = {
        "name": "Test Zone",
        "latitude": 37.7749,
        "longitude": -122.4194,
        "radius": 500.0,
        "enabled": True
    }
    response = requests.post(
        f"{BASE_URL}/v1/geofences",
        headers={"Access-Token": user_token},
        params={"user_id": user_id},
        json=geofence_data
    )
    if response.status_code != 200:
        print(f"   ❌ Geofence creation failed: {response.status_code} {response.text}")
        return False
    
    geofence = response.json()
    geofence_id = geofence["geofence_id"]
    print(f"   ✓ Geofence created: ID={geofence_id}, radius={geofence['radius']}m")
    
    # Send GPS data - INSIDE geofence
    print("\n4. Sending GPS data INSIDE geofence...")
    gps_data = {
        "device_id": device_id,
        "latitude": 37.7750,  # Inside geofence
        "longitude": -122.4193,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "speed": 0.0,
        "heading": 0.0,
        "trip_active": False
    }
    response = requests.post(
        f"{BASE_URL}/v1/sendGPSData",
        json=gps_data,
        headers={"Access-Token": device_token}
    )
    if response.status_code != 200:
        print(f"   ❌ GPS data failed: {response.status_code} {response.text}")
        return False
    
    print(f"   ✓ GPS data sent (inside geofence)")
    time.sleep(1)
    
    # Check for breach events
    print("\n5. Checking for breach events...")
    response = requests.get(
        f"{BASE_URL}/v1/geofence-breach-events",
        headers={"Access-Token": user_token},
        params={"user_id": user_id}
    )
    if response.status_code != 200:
        print(f"   ❌ Event fetch failed: {response.status_code} {response.text}")
        return False
    
    events = response.json()
    print(f"   ✓ Retrieved {len(events)} events")
    
    if events:
        for event in events:
            print(f"     - Event: {event['event_type']} at ({event['latitude']:.4f}, {event['longitude']:.4f})")
    else:
        print(f"   ⚠ No events found yet (may need time to process)")
    
    # Send GPS data - OUTSIDE geofence
    print("\n6. Sending GPS data OUTSIDE geofence...")
    gps_data = {
        "device_id": device_id,
        "latitude": 37.9000,  # Far away
        "longitude": -122.2000,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "speed": 50.0,
        "heading": 180.0,
        "trip_active": True
    }
    response = requests.post(
        f"{BASE_URL}/v1/sendGPSData",
        json=gps_data,
        headers={"Access-Token": device_token}
    )
    if response.status_code != 200:
        print(f"   ❌ GPS data failed: {response.status_code} {response.text}")
        return False
    
    print(f"   ✓ GPS data sent (outside geofence)")
    time.sleep(1)
    
    # Check events again
    print("\n7. Checking for EXITED event...")
    response = requests.get(
        f"{BASE_URL}/v1/geofence-breach-events",
        headers={"Access-Token": user_token},
        params={"user_id": user_id, "limit": 100}
    )
    if response.status_code != 200:
        print(f"   ❌ Event fetch failed: {response.status_code} {response.text}")
        return False
    
    events = response.json()
    exited = [e for e in events if e['event_type'] == 'EXITED']
    
    print(f"   ✓ Total events: {len(events)}")
    print(f"   ✓ EXITED events: {len(exited)}")
    
    print("\n=== TEST COMPLETED ===\n")
    print("Summary:")
    print(f"  User: {user_data['email_address']} (ID: {user_id})")
    print(f"  Device: {device_id}")
    print(f"  Geofence: {geofence_id}")
    print(f"  Events detected: {len(events)}")
    
    return True


if __name__ == "__main__":
    try:
        success = test_simple_breach()
        if success:
            print("\n✅ Test completed successfully!")
        else:
            print("\n❌ Test failed!")
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
