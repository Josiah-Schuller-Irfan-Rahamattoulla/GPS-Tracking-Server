#!/usr/bin/env python3
"""
Test that toggling kill switch in the app propagates to the device via WebSocket instantly.
Flow: create user+device+link, connect device to /v1/ws/devices/{id}, then PUT controls (kill on);
assert device receives device_control_response within a short time.
"""
import asyncio
import json
import os
import random
import sys
import time

import requests

try:
    import websockets
except ImportError:
    print("Install websockets: pip install websockets")
    sys.exit(1)

BASE_HTTP = os.getenv("SMOKE_BASE_URL", "http://localhost:8000")
BASE_WS = BASE_HTTP.replace("http://", "ws://").replace("https://", "wss://")


def setup_user_and_device():
    """Create user, register device, link. Returns (user_id, user_token, device_id, device_token)."""
    now_ms = int(time.time() * 1000)
    rnd = random.randint(0, 999_999)
    user = {
        "email_address": f"killswitch_ws_{now_ms}_{rnd}@example.com",
        "phone_number": f"+1999{now_ms % 10_000_000:07d}{rnd % 1_000:03d}",
        "name": "Kill Switch WS Test",
        "password": "Pass123!",
    }
    device_id = 700_000 + (rnd % 100_000)
    device_token = f"ks_ws_{now_ms}_{rnd}"
    device = {
        "device_id": device_id,
        "access_token": device_token,
        "sms_number": f"+1888{now_ms % 10_000_000:07d}{(rnd + 1) % 1_000:03d}",
    }
    r = requests.post(f"{BASE_HTTP}/v1/signup", json=user, timeout=10)
    r.raise_for_status()
    user_id = r.json()["user_id"]
    user_token = r.json()["access_token"]
    requests.post(f"{BASE_HTTP}/v1/registerDevice", json=device, timeout=10).raise_for_status()
    requests.post(
        f"{BASE_HTTP}/v1/registerDeviceToUser",
        headers={"Access-Token": user_token},
        params={"user_id": user_id},
        json={"device_id": device_id, "access_token": device_token},
        timeout=10,
    ).raise_for_status()
    return user_id, user_token, device_id, device_token


async def run_killswitch_ws_test():
    print("Setting up user and device...")
    user_id, user_token, device_id, device_token = setup_user_and_device()
    print(f"  user_id={user_id}, device_id={device_id}")

    received = asyncio.get_event_loop().create_future()

    async def device_listener():
        uri = f"{BASE_WS}/v1/ws/devices/{device_id}?token={device_token}"
        async with websockets.connect(uri, close_timeout=5) as ws:
            while True:
                msg = await ws.recv()
                data = json.loads(msg)
                if data.get("type") == "device_control_response":
                    if not received.done():
                        received.set_result(data)
                    return
                if data.get("type") == "pong":
                    continue

    async def put_kill_switch_after_delay():
        await asyncio.sleep(0.5)  # give device time to connect
        # Kill switch = all four controls True (same as app)
        r = requests.put(
            f"{BASE_HTTP}/v1/devices/{device_id}/controls",
            headers={"Access-Token": user_token},
            params={"user_id": user_id},
            json={"control_1": True, "control_2": True, "control_3": True, "control_4": True},
            timeout=10,
        )
        r.raise_for_status()
        print("  PUT /devices/{id}/controls (kill ON) -> 200")

    listener = asyncio.create_task(device_listener())
    putter = asyncio.create_task(put_kill_switch_after_delay())

    try:
        msg = await asyncio.wait_for(received, timeout=5.0)
    except asyncio.TimeoutError:
        listener.cancel()
        print("FAIL: Device did not receive device_control_response within 5s")
        return False

    data = msg.get("data") or msg
    if not all((data.get("control_1"), data.get("control_2"), data.get("control_3"), data.get("control_4"))):
        print("FAIL: Received control message but kill switch state not all True:", data)
        return False

    print("PASS: Device received device_control_response with kill switch ON (control_1..4=True) via WebSocket.")
    listener.cancel()
    try:
        await listener
    except asyncio.CancelledError:
        pass
    return True


def main():
    print("Kill switch WebSocket propagation test")
    print(f"  BASE_HTTP={BASE_HTTP}")
    print(f"  BASE_WS={BASE_WS}")
    try:
        ok = asyncio.run(run_killswitch_ws_test())
    except requests.exceptions.ConnectionError as e:
        print(f"Connection error (is the server up?): {e}")
        sys.exit(2)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
