#!/usr/bin/env python3
"""
Test script for new server endpoints (items 1-8).
Run this after starting the server to verify all new features work.

Usage:
    python test_new_endpoints.py --base-url http://localhost:8000
"""

import argparse
import requests
import json
from datetime import datetime, timedelta

def test_endpoint(method, url, headers=None, data=None, description=""):
    """Test an endpoint and print results."""
    print(f"\n{'='*60}")
    print(f"Testing: {description}")
    print(f"{method} {url}")
    if data:
        print(f"Body: {json.dumps(data, indent=2, default=str)}")
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=10)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data, timeout=10)
        elif method == "PUT":
            response = requests.put(url, headers=headers, json=data, timeout=10)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers, timeout=10)
        
        print(f"Status: {response.status_code}")
        if response.status_code < 400:
            print(f"Response: {json.dumps(response.json(), indent=2, default=str)}")
            return response.json()
        else:
            print(f"Error: {response.text}")
            return None
    except Exception as e:
        print(f"Exception: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Test new GPS tracking server endpoints")
    parser.add_argument("--base-url", default="http://localhost:8000", help="Base URL of the API")
    args = parser.parse_args()
    
    base_url = args.base_url.rstrip('/')
    
    print("="*60)
    print("GPS Tracking Server - New Endpoints Test")
    print("="*60)
    
    # Test 1: Health check
    print("\n[TEST 1] Health Check")
    health = test_endpoint("GET", f"{base_url}/health", description="Health check")
    if not health:
        print("❌ Server not responding. Make sure it's running.")
        return
    
    # Test 2: Create test user
    print("\n[TEST 2] Create Test User")
    test_user = {
        "email_address": f"test_{datetime.now().timestamp()}@example.com",
        "phone_number": f"+61{int(datetime.now().timestamp()) % 10000000000}",
        "name": "Test User",
        "password": "testpass123"
    }
    signup_response = test_endpoint("POST", f"{base_url}/v1/signup", data=test_user, description="User signup")
    if not signup_response:
        print("❌ Failed to create user")
        return
    
    user_token = signup_response.get("access_token")
    user_id = signup_response.get("user_id")
    print(f"✅ User created: ID={user_id}, Token={user_token[:20]}...")
    
    headers = {"Access-Token": user_token}
    
    # Test 3: Register test device
    print("\n[TEST 3] Register Test Device")
    device_id = int(datetime.now().timestamp()) % 1000000
    device_token = f"device_token_{device_id}"
    device_data = {
        "device_id": device_id,
        "access_token": device_token,
        "sms_number": f"+61{int(datetime.now().timestamp()) % 10000000000}",
        "name": "Test Vehicle",
        "control_1": False,
        "control_2": False
    }
    device_response = test_endpoint("POST", f"{base_url}/v1/registerDevice", data=device_data, description="Device registration")
    if not device_response:
        print("❌ Failed to register device")
        return
    print(f"✅ Device registered: ID={device_id}")
    
    # Test 4: Link device to user
    print("\n[TEST 4] Link Device to User")
    device_headers = {"Access-Token": device_token}
    link_data = {
        "device_id": device_id,
        "user_id": user_id
    }
    link_response = test_endpoint("POST", f"{base_url}/v1/registerDeviceToUser", headers=device_headers, data=link_data, description="Link device to user")
    if not link_response:
        print("❌ Failed to link device")
        return
    print("✅ Device linked to user")
    
    # Test 5: Send GPS data with new fields
    print("\n[TEST 5] Send GPS Data (with speed, heading, trip_active)")
    gps_data = {
        "device_id": device_id,
        "latitude": -37.8136,
        "longitude": 144.9631,
        "timestamp": datetime.utcnow().isoformat(),
        "speed": 65.5,
        "heading": 180.0,
        "trip_active": True
    }
    gps_response = test_endpoint("POST", f"{base_url}/v1/sendGPSData", headers=device_headers, data=gps_data, description="Send GPS data with extensions")
    if not gps_response:
        print("❌ Failed to send GPS data")
        return
    print("✅ GPS data sent with speed, heading, trip_active")
    
    # Test 6: Get single device
    print("\n[TEST 6] Get Single Device")
    device_get = test_endpoint("GET", f"{base_url}/v1/devices/{device_id}?user_id={user_id}", headers=headers, description="Get device details")
    if not device_get:
        print("❌ Failed to get device")
        return
    print(f"✅ Device retrieved: name={device_get.get('name')}, version={device_get.get('control_version')}")
    
    # Test 7: Update device controls
    print("\n[TEST 7] Update Device Controls")
    controls_data = {
        "control_1": True,
        "control_2": True,
        "expected_version": device_get.get("control_version", 0)
    }
    controls_response = test_endpoint("PUT", f"{base_url}/v1/devices/{device_id}/controls?user_id={user_id}", headers=headers, data=controls_data, description="Update device controls")
    if not controls_response:
        print("❌ Failed to update controls")
        return
    print(f"✅ Controls updated: version={controls_response.get('control_version')}")
    
    # Test 8: Get trip status
    print("\n[TEST 8] Get Trip Status")
    trip_response = test_endpoint("GET", f"{base_url}/v1/devices/{device_id}/trip?user_id={user_id}", headers=headers, description="Get trip status")
    if not trip_response:
        print("❌ Failed to get trip status")
        return
    print(f"✅ Trip status: active={trip_response.get('trip_active')}")
    
    # Test 9: Create geofence
    print("\n[TEST 9] Create Geofence")
    geofence_data = {
        "name": "Home",
        "latitude": -37.8136,
        "longitude": 144.9631,
        "radius": 500.0,
        "enabled": True
    }
    geofence_create = test_endpoint("POST", f"{base_url}/v1/geofences?user_id={user_id}", headers=headers, data=geofence_data, description="Create geofence")
    if not geofence_create:
        print("❌ Failed to create geofence")
        return
    geofence_id = geofence_create.get("geofence_id")
    print(f"✅ Geofence created: ID={geofence_id}")
    
    # Test 10: Get geofences
    print("\n[TEST 10] Get Geofences")
    geofences = test_endpoint("GET", f"{base_url}/v1/geofences?user_id={user_id}", headers=headers, description="Get all geofences")
    if not geofences:
        print("❌ Failed to get geofences")
        return
    print(f"✅ Retrieved {len(geofences)} geofence(s)")
    
    # Test 11: Update geofence
    print("\n[TEST 11] Update Geofence")
    geofence_update_data = {
        "enabled": False,
        "radius": 1000.0
    }
    geofence_update = test_endpoint("PUT", f"{base_url}/v1/geofences/{geofence_id}?user_id={user_id}", headers=headers, data=geofence_update_data, description="Update geofence")
    if not geofence_update:
        print("❌ Failed to update geofence")
        return
    print(f"✅ Geofence updated: enabled={geofence_update.get('enabled')}, radius={geofence_update.get('radius')}")
    
    # Test 12: Get user devices (should include name)
    print("\n[TEST 12] Get User Devices (with name)")
    devices = test_endpoint("GET", f"{base_url}/v1/devices?user_id={user_id}", headers=headers, description="Get user devices")
    if not devices:
        print("❌ Failed to get devices")
        return
    print(f"✅ Retrieved {len(devices)} device(s)")
    if devices and devices[0].get("name"):
        print(f"✅ Device name present: {devices[0].get('name')}")
    
    # Test 13: Get GPS data (should include speed/heading)
    print("\n[TEST 13] Get GPS Data (with speed/heading)")
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(hours=1)
    gps_get = test_endpoint("GET", f"{base_url}/v1/GPSData?user_id={user_id}&device_id={device_id}&start_time={start_time.isoformat()}&end_time={end_time.isoformat()}", headers=headers, description="Get GPS data")
    if not gps_get:
        print("❌ Failed to get GPS data")
        return
    gps_points = gps_get.get("gps_data", [])
    print(f"✅ Retrieved {len(gps_points)} GPS point(s)")
    if gps_points:
        point = gps_points[0]
        print(f"✅ GPS data includes: speed={point.get('speed')}, heading={point.get('heading')}, trip_active={point.get('trip_active')}")
    
    # Test 14: Delete geofence
    print("\n[TEST 14] Delete Geofence")
    geofence_delete = test_endpoint("DELETE", f"{base_url}/v1/geofences/{geofence_id}?user_id={user_id}", headers=headers, description="Delete geofence")
    if not geofence_delete:
        print("❌ Failed to delete geofence")
        return
    print("✅ Geofence deleted")
    
    print("\n" + "="*60)
    print("✅ ALL TESTS COMPLETED")
    print("="*60)
    print(f"\nTest User ID: {user_id}")
    print(f"Test Device ID: {device_id}")
    print(f"User Token: {user_token[:30]}...")
    print(f"Device Token: {device_token}")

if __name__ == "__main__":
    main()

















