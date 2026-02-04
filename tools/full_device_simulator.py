#!/usr/bin/env python3
"""
Full Device Simulator for GPS Tracking System
Simulates a complete GPS device lifecycle:
- Registration
- Linking to user
- GPS data transmission with movement patterns
- Kill switch testing
- Trip simulation
- Geofence testing
"""

import os
import requests
import time
import random
import math
from datetime import datetime, timezone
from typing import Tuple, Optional

# Configuration
BASE_URL = "http://gpstracking.josiahschuller.au"
DEVICE_ID = random.randint(100000, 999999)
DEVICE_TOKEN = f"sim_device_{DEVICE_ID}_{int(time.time())}"
SMS_NUMBER = f"+614{random.randint(10000000, 99999999)}"
USER_EMAIL = os.getenv("USER_EMAIL", "irfanrahamattoulla@hotmail.com")
USER_PASSWORD = os.getenv("USER_PASSWORD", "pass")
USER_ACCESS_TOKEN = os.getenv("USER_ACCESS_TOKEN")  # Optional; if not set we will login automatically

# Starting position (Melbourne, Australia)
START_LAT = -37.8136
START_LON = 144.9631

# Movement patterns
SPEED_STATIONARY = 0
SPEED_WALKING = 5  # km/h
SPEED_DRIVING = 60  # km/h
SPEED_HIGHWAY = 100  # km/h

# Simulation state
current_lat = START_LAT
current_lon = START_LON
current_heading = 0  # degrees
current_speed = 0  # km/h
trip_active = False
kill_switch_active = False


def print_banner(text: str):
    """Print a formatted banner"""
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)


def print_step(step: int, text: str):
    """Print a step with timestamp"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"\n[{timestamp}] Step {step}: {text}")


def print_success(text: str):
    """Print success message"""
    print(f"[OK] {text}")


def print_error(text: str):
    """Print error message"""
    print(f"[FAIL] {text}")


def print_info(text: str):
    """Print info message"""
    print(f"[*] {text}")


def ensure_user_access_token() -> Optional[str]:
    """Return a user access token, logging in if needed."""
    global USER_ACCESS_TOKEN
    if USER_ACCESS_TOKEN:
        return USER_ACCESS_TOKEN
    try:
        print_info("Logging in to obtain user access token...")
        resp = requests.post(
            f"{BASE_URL}/v1/login",
            json={"email_address": USER_EMAIL, "password": USER_PASSWORD},
            timeout=10,
            verify=False,
        )
        if not resp.ok:
            print_error(f"Login failed (HTTP {resp.status_code})")
            print_error(f"Response: {resp.text}")
            return None
        data = resp.json()
        token = data.get("access_token")
        if not token:
            print_error("Login response missing access_token")
            return None
        USER_ACCESS_TOKEN = token
        print_success("Obtained user access token via login")
        return token
    except Exception as e:
        print_error(f"Login error: {e}")
        return None


def register_device() -> bool:
    """Register the device with the server"""
    print_step(1, "Registering Device")
    print_info(f"Device ID: {DEVICE_ID}")
    print_info(f"SMS Number: {SMS_NUMBER}")
    print_info(f"Token: {DEVICE_TOKEN[:20]}...")
    
    try:
        response = requests.post(
            f"{BASE_URL}/v1/registerDevice",
            json={
                "device_id": DEVICE_ID,
                "access_token": DEVICE_TOKEN,
                "sms_number": SMS_NUMBER
            },
            timeout=10,
            verify=False
        )
        
        if response.ok:
            print_success(f"Device registered successfully (HTTP {response.status_code})")
            print_info(f"Response: {response.json()}")
            return True
        else:
            print_error(f"Registration failed (HTTP {response.status_code})")
            print_error(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print_error(f"Registration error: {e}")
        return False


def link_to_user(user_id: int) -> bool:
    """Link device to a user account"""
    print_step(2, "Linking Device to User")
    print_info(f"User ID: {user_id}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/v1/registerDeviceToUser",
            headers={"Access-Token": DEVICE_TOKEN},
            json={
                "device_id": DEVICE_ID,
                "user_id": user_id
            },
            timeout=10,
            verify=False
        )
        
        if response.ok:
            print_success(f"Device linked to user successfully (HTTP {response.status_code})")
            print_info(f"Response: {response.json()}")
            return True
        else:
            print_error(f"Linking failed (HTTP {response.status_code})")
            print_error(f"Response: {response.text}")
            return False
            
    except Exception as e:
        print_error(f"Linking error: {e}")
        return False


def send_gps_data(
    latitude: float,
    longitude: float,
    speed: float,
    heading: float,
    accuracy: float = 10.0,
    trip_active: bool = False
) -> bool:
    """Send GPS data to server"""
    timestamp = datetime.now(timezone.utc).isoformat()
    
    payload = {
        "device_id": DEVICE_ID,
        "latitude": latitude,
        "longitude": longitude,
        "timestamp": timestamp,
        "speed": speed,
        "heading": heading,
        "accuracy": accuracy,
        "trip_active": trip_active
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/v1/sendGPSData",
            headers={"Access-Token": DEVICE_TOKEN},
            json=payload,
            timeout=10,
            verify=False
        )
        
        if response.ok:
            return True
        else:
            print_error(f"GPS send failed (HTTP {response.status_code}): {response.text}")
            return False
            
    except Exception as e:
        print_error(f"GPS send error: {e}")
        return False


def check_device_controls() -> dict:
    """Check current device control settings"""
    try:
        response = requests.get(
            f"{BASE_URL}/v1/device/{DEVICE_ID}/controls",
            headers={"Access-Token": DEVICE_TOKEN},
            timeout=10,
            verify=False
        )
        
        if response.ok:
            return response.json()
        else:
            return {}
            
    except Exception as e:
        print_error(f"Control check error: {e}")
        return {}


def move_in_direction(heading_deg: float, speed_kmh: float, duration_sec: float = 1.0) -> Tuple[float, float]:
    """
    Calculate new position based on heading and speed
    Returns: (new_lat, new_lon)
    """
    global current_lat, current_lon
    
    # Convert to radians
    heading_rad = math.radians(heading_deg)
    
    # Distance traveled in km
    distance_km = (speed_kmh / 3600) * duration_sec
    
    # Earth radius in km
    R = 6371.0
    
    # Convert latitude to radians
    lat_rad = math.radians(current_lat)
    lon_rad = math.radians(current_lon)
    
    # Calculate new position
    new_lat_rad = math.asin(
        math.sin(lat_rad) * math.cos(distance_km / R) +
        math.cos(lat_rad) * math.sin(distance_km / R) * math.cos(heading_rad)
    )
    
    new_lon_rad = lon_rad + math.atan2(
        math.sin(heading_rad) * math.sin(distance_km / R) * math.cos(lat_rad),
        math.cos(distance_km / R) - math.sin(lat_rad) * math.sin(new_lat_rad)
    )
    
    new_lat = math.degrees(new_lat_rad)
    new_lon = math.degrees(new_lon_rad)
    
    current_lat = new_lat
    current_lon = new_lon
    
    return new_lat, new_lon


def simulate_stationary(duration_sec: int = 10):
    """Simulate stationary device"""
    print_step(3, f"Simulating Stationary Device ({duration_sec}s)")
    global current_speed
    current_speed = 0
    
    for i in range(duration_sec):
        # Add slight GPS jitter (realistic GPS drift)
        lat = current_lat + random.uniform(-0.00001, 0.00001)
        lon = current_lon + random.uniform(-0.00001, 0.00001)
        
        success = send_gps_data(lat, lon, current_speed, current_heading, trip_active=trip_active)
        if success and i % 3 == 0:
            print(f"  [{i+1}/{duration_sec}] Position: {lat:.6f}, {lon:.6f}")
        
        time.sleep(1)
    
    print_success(f"Sent {duration_sec} stationary GPS updates")


def simulate_walking(duration_sec: int = 15, direction: Optional[float] = None):
    """Simulate walking movement"""
    print_step(4, f"Simulating Walking ({duration_sec}s)")
    global current_speed, current_heading
    current_speed = SPEED_WALKING
    
    if direction is not None:
        current_heading = direction
    else:
        current_heading = random.uniform(0, 360)
    
    print_info(f"Walking at {current_speed} km/h, heading {current_heading:.0f}°")
    
    for i in range(duration_sec):
        lat, lon = move_in_direction(current_heading, current_speed, 1.0)
        
        # Add some random wobble to heading (realistic walking pattern)
        current_heading = (current_heading + random.uniform(-15, 15)) % 360
        
        success = send_gps_data(lat, lon, current_speed, current_heading, trip_active=trip_active)
        if success and i % 5 == 0:
            print(f"  [{i+1}/{duration_sec}] Position: {lat:.6f}, {lon:.6f} | Heading: {current_heading:.0f}°")
        
        time.sleep(1)
    
    print_success(f"Walked approximately {(current_speed / 3600) * duration_sec * 1000:.0f} meters")


def simulate_driving(duration_sec: int = 20, highway: bool = False):
    """Simulate driving movement"""
    speed = SPEED_HIGHWAY if highway else SPEED_DRIVING
    mode = "Highway Driving" if highway else "City Driving"
    
    print_step(5, f"Simulating {mode} ({duration_sec}s)")
    global current_speed, current_heading, trip_active
    current_speed = speed
    trip_active = True
    
    # Random heading for driving
    current_heading = random.uniform(0, 360)
    print_info(f"Driving at {current_speed} km/h, heading {current_heading:.0f}°")
    
    for i in range(duration_sec):
        lat, lon = move_in_direction(current_heading, current_speed, 1.0)
        
        # Gradual heading changes (realistic driving)
        if random.random() < 0.2:  # 20% chance to turn
            current_heading = (current_heading + random.uniform(-30, 30)) % 360
        
        # Speed variations
        speed_variation = random.uniform(-5, 5)
        actual_speed = max(0, current_speed + speed_variation)
        
        success = send_gps_data(lat, lon, actual_speed, current_heading, trip_active=True)
        if success and i % 5 == 0:
            print(f"  [{i+1}/{duration_sec}] Position: {lat:.6f}, {lon:.6f} | Speed: {actual_speed:.0f} km/h | Heading: {current_heading:.0f}°")
        
        time.sleep(1)
    
    distance_km = (current_speed / 3600) * duration_sec
    print_success(f"Drove approximately {distance_km:.2f} km")


def simulate_trip():
    """Simulate a complete trip"""
    print_banner("SIMULATING TRIP")
    global trip_active
    
    # Start trip
    print_info("Starting trip...")
    trip_active = True
    
    # Initial stationary
    simulate_stationary(5)
    
    # Start driving
    simulate_driving(15, highway=False)
    
    # Highway section
    simulate_driving(20, highway=True)
    
    # Slow down
    simulate_driving(10, highway=False)
    
    # Stop at destination
    print_info("Arriving at destination...")
    simulate_stationary(5)
    
    # End trip
    trip_active = False
    print_success("Trip completed")


def test_kill_switch(user_id: int):
    """Test kill switch functionality"""
    print_banner("TESTING KILL SWITCH")
    global kill_switch_active
    token = ensure_user_access_token()
    if not token:
        print_error("Cannot proceed without user access token.")
        return
    
    print_step(6, "Activating Kill Switch")
    print_info("Sending kill switch command via API...")
    
    try:
        # Activate kill switch
        response = requests.put(
            f"{BASE_URL}/v1/devices/{DEVICE_ID}/controls",
            params={"user_id": user_id},
            headers={"Access-Token": token},  # user token required
            json={
                "control_1": True,  # Kill switch
                "control_2": False,
                "control_3": False,
                "control_4": False
            },
            timeout=10,
            verify=False
        )
        
        if response.ok:
            print_success("Kill switch ACTIVATED")
            kill_switch_active = True
            
            # Check controls
            time.sleep(2)
            controls = check_device_controls()
            print_info(f"Current controls: {controls}")
            
            # Simulate device stopping
            print_info("Device responding to kill switch...")
            simulate_stationary(10)
            
            # Deactivate kill switch
            print_step(7, "Deactivating Kill Switch")
            response = requests.put(
                f"{BASE_URL}/v1/devices/{DEVICE_ID}/controls",
                params={"user_id": user_id},
                headers={"Access-Token": token},  # user token required
                json={
                    "control_1": False,  # Kill switch off
                    "control_2": False,
                    "control_3": False,
                    "control_4": False
                },
                timeout=10,
                verify=False
            )
            
            if response.ok:
                print_success("Kill switch DEACTIVATED")
                kill_switch_active = False
            
        else:
            print_error(f"Kill switch activation failed (HTTP {response.status_code})")
            
    except Exception as e:
        print_error(f"Kill switch test error: {e}")


def simulate_circle_pattern(radius_km: float = 0.5, points: int = 20):
    """Simulate circular movement (useful for geofence testing)"""
    print_step(8, f"Simulating Circular Pattern (radius: {radius_km} km)")
    global current_speed, current_heading
    current_speed = SPEED_DRIVING
    
    center_lat = current_lat
    center_lon = current_lon
    
    for i in range(points):
        angle = (i / points) * 2 * math.pi
        
        # Calculate position on circle
        lat_offset = radius_km * math.cos(angle) / 111.0  # ~111 km per degree latitude
        lon_offset = radius_km * math.sin(angle) / (111.0 * math.cos(math.radians(center_lat)))
        
        lat = center_lat + lat_offset
        lon = center_lon + lon_offset
        
        # Calculate heading (tangent to circle)
        current_heading = (math.degrees(angle) + 90) % 360
        
        send_gps_data(lat, lon, current_speed, current_heading, trip_active=True)
        print(f"  [{i+1}/{points}] Position: {lat:.6f}, {lon:.6f} | Heading: {current_heading:.0f}°")
        
        time.sleep(2)
    
    print_success("Completed circular pattern")


def main():
    """Main simulation flow"""
    print_banner("GPS DEVICE SIMULATOR - FULL TEST")
    print(f"Device ID: {DEVICE_ID}")
    print(f"Device Token: {DEVICE_TOKEN[:30]}...")
    print(f"SMS Number: {SMS_NUMBER}")
    print(f"Starting Position: {START_LAT:.6f}, {START_LON:.6f}")
    
    # Step 1: Register device
    if not register_device():
        print_error("Failed to register device. Exiting.")
        return
    
    time.sleep(2)
    
    # Step 2: Link to user (default to user ID 2 - irfanrahamattoulla)
    user_id = 2
    print("\n" + "=" * 60)
    print(f"Linking device to User ID {user_id} (irfanrahamattoulla)")
    
    if not link_to_user(user_id):
        print_error("Failed to link device. Exiting.")
        return
    
    time.sleep(2)
    
    # Step 3: Send initial position
    print_step(3, "Sending Initial Position")
    send_gps_data(current_lat, current_lon, 0, 0, trip_active=False)
    print_success(f"Initial position sent: {current_lat:.6f}, {current_lon:.6f}")
    
    time.sleep(2)
    
    # Step 4: Run simulations
    print("\n" + "=" * 60)
    print("SELECT SIMULATION MODE:")
    print("1. Full automated test (stationary -> walking -> driving -> trip -> kill switch)")
    print("2. Stationary only")
    print("3. Walking only")
    print("4. Driving only")
    print("5. Complete trip simulation")
    print("6. Kill switch test")
    print("7. Circular pattern (geofence testing)")
    print("8. Continuous random movement")
    
    mode = input("\nEnter mode (1-8): ").strip()
    
    if mode == "1":
        # Full automated test
        simulate_stationary(10)
        time.sleep(2)
        simulate_walking(15)
        time.sleep(2)
        simulate_driving(20)
        time.sleep(2)
        simulate_trip()
        time.sleep(2)
        test_kill_switch(user_id)
        time.sleep(2)
        simulate_circle_pattern()
        
    elif mode == "2":
        duration = int(input("Duration (seconds): ").strip() or "30")
        simulate_stationary(duration)
        
    elif mode == "3":
        duration = int(input("Duration (seconds): ").strip() or "30")
        simulate_walking(duration)
        
    elif mode == "4":
        duration = int(input("Duration (seconds): ").strip() or "30")
        highway = input("Highway speed? (y/n): ").strip().lower() == 'y'
        simulate_driving(duration, highway)
        
    elif mode == "5":
        simulate_trip()
        
    elif mode == "6":
        test_kill_switch(user_id)
        
    elif mode == "7":
        radius = float(input("Radius (km): ").strip() or "0.5")
        points = int(input("Number of points: ").strip() or "20")
        simulate_circle_pattern(radius, points)
        
    elif mode == "8":
        # Continuous random movement
        print_banner("CONTINUOUS RANDOM MOVEMENT")
        print_info("Press Ctrl+C to stop")
        
        try:
            while True:
                pattern = random.choice(["stationary", "walking", "driving"])
                
                if pattern == "stationary":
                    simulate_stationary(random.randint(5, 15))
                elif pattern == "walking":
                    simulate_walking(random.randint(10, 20))
                elif pattern == "driving":
                    simulate_driving(random.randint(15, 30), random.choice([True, False]))
                
                time.sleep(2)
                
        except KeyboardInterrupt:
            print("\n")
            print_info("Simulation stopped by user")
    
    print_banner("SIMULATION COMPLETE")
    print_success("Device is now registered and has location history")
    print_info(f"Device ID: {DEVICE_ID}")
    print_info(f"Final Position: {current_lat:.6f}, {current_lon:.6f}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n")
        print_info("Simulation interrupted by user")
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
