#!/usr/bin/env python3
"""
Test that device controls (kill switch) are cached server-side and visible
to a device via GET /v1/getDeviceControls, independent of WebSocket state.

Usage:
    SMOKE_BASE_URL=https://gpstracking.josiahschuller.au python tools/test_kill_cache.py
"""
import os
import random
import time
import uuid

import requests


def main():
    base = os.getenv("SMOKE_BASE_URL", "http://localhost:8000").rstrip("/")
    http_base = f"{base}/v1"

    ts = int(time.time() * 1000)
    rnd = random.randint(0, 999_999)

    # Create user
    user = {
        "email_address": f"killcache_{ts}_{rnd}@example.com",
        "phone_number": f"+1779{ts % 10000000:07d}{rnd % 1000:03d}",
        "name": "Kill Cache Test User",
        "password": "Pass123!",
    }
    r = requests.post(f"{http_base}/signup", json=user, timeout=20)
    r.raise_for_status()
    body = r.json()
    user_id = body["user_id"]
    user_token = body["access_token"]
    print("User created:", user_id)

    # Create device
    dev_id = 800000 + (uuid.uuid4().int & ((1 << 20) - 1))
    dev_token = f"killcache_dev_{ts}_{rnd}"
    device = {
        "device_id": dev_id,
        "access_token": dev_token,
        "sms_number": f"+1668{ts % 10000000:07d}{rnd % 1000:03d}",
        "name": "Kill Cache Test Device",
    }
    requests.post(f"{http_base}/registerDevice", json=device, timeout=20).raise_for_status()
    print("Device registered:", dev_id)

    # Link device to user
    link = {
        "device_id": dev_id,
        "access_token": dev_token,
    }
    requests.post(
        f"{http_base}/registerDeviceToUser",
        headers={"Access-Token": user_token},
        params={"user_id": user_id},
        json=link,
        timeout=20,
    ).raise_for_status()
    print("Device linked to user.")

    # 1) Read initial controls via device-friendly endpoint
    def get_controls():
        r0 = requests.get(
            f"{http_base}/getDeviceControls",
            params={"device_id": dev_id},
            headers={"Access-Token": dev_token},
            timeout=15,
        )
        r0.raise_for_status()
        return r0.json()

    init_ctrl = get_controls()
    print("Initial controls:", init_ctrl)

    # 2) User sets kill switch ON via HTTP controls endpoint
    desired = {
        "control_1": True,
        "control_2": True,
        "control_3": True,
        "control_4": True,
    }
    r1 = requests.put(
        f"{http_base}/devices/{dev_id}/controls",
        headers={"Access-Token": user_token},
        params={"user_id": user_id},
        json=desired,
        timeout=20,
    )
    r1.raise_for_status()
    print("Controls updated by user; response:", r1.json())

    # 3) Immediately re-read getDeviceControls as the device – this should see the new state,
    # even if device WS was never connected or is currently offline.
    updated = get_controls()
    print("Updated controls from getDeviceControls:", updated)

    for key, wanted in desired.items():
        actual = updated.get(key)
        assert actual is True, f"{key} expected True but got {actual}"

    print("PASS: Cached controls visible via getDeviceControls (kill switch ON).")


if __name__ == "__main__":
    main()

