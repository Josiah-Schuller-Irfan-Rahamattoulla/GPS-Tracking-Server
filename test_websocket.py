"""Quick WebSocket connectivity test for GPS Tracking Server."""

import asyncio
import websockets
import json
import sys

async def test_device_ws():
    """Test device WebSocket connection."""
    try:
        device_id = 1
        token = "test-device-token"
        uri = f"ws://localhost:8000/v1/ws/devices/{device_id}?token={token}"
        
        print(f"Testing device WebSocket at {uri}...")
        async with websockets.connect(uri) as websocket:
            print("✓ Device WebSocket connected!")
            
            # Send a ping
            await websocket.send(json.dumps({"type": "ping"}))
            response = await websocket.recv()
            response_data = json.loads(response)
            print(f"✓ Received pong: {response_data}")
            
            # Send a location update
            location_msg = {
                "type": "location_update",
                "data": {
                    "device_id": device_id,
                    "latitude": 40.7128,
                    "longitude": -74.0060,
                    "speed": 45.5,
                    "heading": 90
                }
            }
            await websocket.send(json.dumps(location_msg))
            print(f"✓ Sent location update: {location_msg}")
            
            return True
    except Exception as e:
        print(f"✗ Device WebSocket test failed: {e}")
        return False


async def test_user_ws():
    """Test user WebSocket connection."""
    try:
        device_id = 1
        token = "test-user-token"
        uri = f"ws://localhost:8000/v1/ws/users/{device_id}?token={token}"
        
        print(f"\nTesting user WebSocket at {uri}...")
        async with websockets.connect(uri) as websocket:
            print("✓ User WebSocket connected!")
            
            # Send a ping
            await websocket.send(json.dumps({"type": "ping"}))
            response = await websocket.recv()
            response_data = json.loads(response)
            print(f"✓ Received pong: {response_data}")
            
            return True
    except Exception as e:
        print(f"✗ User WebSocket test failed: {e}")
        return False


async def test_geofence_ws():
    """Test geofence WebSocket connection."""
    try:
        device_id = 1
        token = "test-user-token"
        uri = f"ws://localhost:8000/v1/ws/geofence/{device_id}?token={token}"
        
        print(f"\nTesting geofence WebSocket at {uri}...")
        async with websockets.connect(uri) as websocket:
            print("✓ Geofence WebSocket connected!")
            
            # Send a ping
            await websocket.send(json.dumps({"type": "ping"}))
            response = await websocket.recv()
            response_data = json.loads(response)
            print(f"✓ Received pong: {response_data}")
            
            return True
    except Exception as e:
        print(f"✗ Geofence WebSocket test failed: {e}")
        return False


async def main():
    print("=" * 60)
    print("GPS Tracking Server - WebSocket Connectivity Tests")
    print("=" * 60)
    
    device_ok = await test_device_ws()
    user_ok = await test_user_ws()
    geofence_ok = await test_geofence_ws()
    
    print("\n" + "=" * 60)
    print("Test Summary:")
    print(f"  Device WebSocket:    {'✓ PASS' if device_ok else '✗ FAIL'}")
    print(f"  User WebSocket:      {'✓ PASS' if user_ok else '✗ FAIL'}")
    print(f"  Geofence WebSocket:  {'✓ PASS' if geofence_ok else '✗ FAIL'}")
    print("=" * 60)
    
    if device_ok and user_ok and geofence_ok:
        print("\n✓ All tests passed!")
        sys.exit(0)
    else:
        print("\n✗ Some tests failed")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
