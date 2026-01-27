#!/usr/bin/env python3
"""
Lightweight simulator to register a device, link it to a user, stream GPS points, and toggle controls.

Usage examples:
  python tools/simulate_device.py --user-id 1 --user-token USER_ACCESS_TOKEN
  python tools/simulate_device.py --user-id 1 --user-token USER_ACCESS_TOKEN --base-url http://172.16.20.18:8000 --points 20 --interval 2

What it does:
- POST /v1/registerDevice               (device token header not required)
- POST /v1/registerDeviceToUser         (Access-Token: device token)
- POST /v1/sendGPSData                  (Access-Token: device token)
- PUT  /v1/devices/{device_id}/controls (Access-Token: user token)

Notes:
- You need a valid user access token for control updates.
- Device endpoints use the device token for Access-Token.
- Generates sensible defaults for device_id, device_token, and sms_number if not provided.
"""

import argparse
import json
import random
import time
from datetime import datetime, timezone
from typing import Iterable, Tuple

import requests

DEFAULT_BASE_URL = "https://gpstracking.josiahschuller.au"


def ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def register_device(base_url: str, device_id: int, device_token: str, sms_number: str) -> dict:
    resp = requests.post(
        f"{base_url}/v1/registerDevice",
        headers={"Content-Type": "application/json"},
        json={
            "device_id": device_id,
            "access_token": device_token,
            "sms_number": sms_number,
        },
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def link_device_to_user(base_url: str, device_id: int, device_token: str, user_id: int) -> dict:
    resp = requests.post(
        f"{base_url}/v1/registerDeviceToUser",
        headers={
            "Content-Type": "application/json",
            "Access-Token": device_token,
        },
        json={"device_id": device_id, "user_id": user_id},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def send_gps(base_url: str, device_id: int, device_token: str, lat: float, lon: float) -> dict:
    resp = requests.post(
        f"{base_url}/v1/sendGPSData",
        headers={
            "Content-Type": "application/json",
            "Access-Token": device_token,
        },
        json={
            "device_id": device_id,
            "latitude": lat,
            "longitude": lon,
            "timestamp": ts(),
        },
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def update_controls(base_url: str, user_token: str, user_id: int, device_id: int, kill_switch: bool) -> dict:
    qs = f"user_id={user_id}"
    resp = requests.put(
        f"{base_url}/v1/devices/{device_id}/controls?{qs}",
        headers={
            "Content-Type": "application/json",
            "Access-Token": user_token,
        },
        json={
            "control_1": kill_switch,
            "control_2": None,
            "control_3": None,
            "control_4": None,
        },
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def path_generator(lat: float, lon: float, step_m: float, count: int) -> Iterable[Tuple[float, float]]:
    # Simple random walk around the starting point.
    # Roughly ~0.00001 degrees ~ 1.1m; scale step_m to degrees.
    deg_per_meter = 1.0 / 111_111.0
    step_deg = step_m * deg_per_meter
    cur_lat, cur_lon = lat, lon
    for _ in range(count):
        cur_lat += random.uniform(-step_deg, step_deg)
        cur_lon += random.uniform(-step_deg, step_deg)
        yield round(cur_lat, 6), round(cur_lon, 6)


def main() -> None:
    parser = argparse.ArgumentParser(description="Simulate a GPS device lifecycle and movement")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="API base URL")
    parser.add_argument("--user-id", type=int, help="User ID to link the device to (auto-generated if omitted)")
    parser.add_argument("--user-token", help="User access token for control updates (auto-generated if omitted)")
    parser.add_argument("--device-id", type=int, help="Device ID (auto-generated if omitted)")
    parser.add_argument("--device-token", help="Device access token (auto-generated if omitted)")
    parser.add_argument("--sms-number", help="Unique SMS number (auto-generated if omitted)")
    parser.add_argument("--start-lat", type=float, help="Starting latitude (random if omitted)")
    parser.add_argument("--start-lon", type=float, help="Starting longitude (random if omitted)")
    parser.add_argument("--points", type=int, default=20, help="Number of GPS points to send")
    parser.add_argument("--interval", type=float, default=2.0, help="Seconds between points")
    parser.add_argument("--step-m", type=float, default=15.0, help="Approx meters moved per step")
    parser.add_argument("--toggle-kill", action="store_true", help="Toggle kill switch on halfway, off at end")
    args = parser.parse_args()

    # Auto-generate all fields with random values if not provided
    device_id = args.device_id or random.randint(100000, 999999)
    device_token = args.device_token or f"test_device_token_{random.randint(1_000_000, 9_999_999)}"
    sms_number = args.sms_number or f"+61{random.randint(4_000_000_000, 4_999_999_999)}"
    user_id = args.user_id or random.randint(1, 10000)
    user_token = args.user_token or f"test_user_token_{random.randint(1_000_000, 9_999_999)}"
    start_lat = args.start_lat if args.start_lat is not None else random.uniform(-37.85, -37.80)  # Melbourne area
    start_lon = args.start_lon if args.start_lon is not None else random.uniform(144.95, 145.00)  # Melbourne area

    print(f"Base URL: {args.base_url}")
    print(f"Device ID: {device_id}")
    print(f"Device Token: {device_token}")
    print(f"SMS Number: {sms_number}")
    print(f"User ID: {user_id}")
    print(f"User Token: {user_token}")
    print(f"Starting Location: {start_lat:.6f}, {start_lon:.6f}")
    print("")

    try:
        print("[1/4] Registering device...")
        reg = register_device(args.base_url, device_id, device_token, sms_number)
        print("    OK:", json.dumps(reg))
    except Exception as e:
        print("    Failed to register device:", e)
        return

    try:
        print("[2/4] Linking device to user...")
        link = link_device_to_user(args.base_url, device_id, device_token, user_id)
        print("    OK:", json.dumps(link))
    except Exception as e:
        print("    Failed to link device to user:", e)
        return

    if args.toggle_kill:
        try:
            print("[3/4] Enabling kill switch (control_1=True)...")
            res = update_controls(args.base_url, user_token, user_id, device_id, True)
            print("    OK:", json.dumps(res))
        except Exception as e:
            print("    Failed to set kill switch:", e)
            return

    print("[4/4] Streaming GPS points...")
    for idx, (lat, lon) in enumerate(path_generator(start_lat, start_lon, args.step_m, args.points), start=1):
        try:
            res = send_gps(args.base_url, device_id, device_token, lat, lon)
            print(f"    #{idx:02d} {lat:.6f}, {lon:.6f} -> {res}")
        except Exception as e:
            print(f"    #{idx:02d} Failed to send GPS: {e}")
            break
        time.sleep(args.interval)

        # Toggle kill switch off near the end when requested
        if args.toggle_kill and idx == args.points // 2:
            try:
                print("    Toggling kill switch OFF (control_1=False)...")
                res = update_controls(args.base_url, user_token, user_id, device_id, False)
                print("    OK:", json.dumps(res))
            except Exception as e:
                print("    Failed to clear kill switch:", e)

    print("Done.")


if __name__ == "__main__":
    main()
