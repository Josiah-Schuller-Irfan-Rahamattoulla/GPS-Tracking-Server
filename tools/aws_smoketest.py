import datetime
import json
import os
import random
import time

import requests


# Set SMOKE_BASE_URL for target (e.g. http://localhost:8000 for Docker)
BASE = os.getenv("SMOKE_BASE_URL", "http://localhost:8000")


def p(label, obj):
    print(f"\n=== {label} ===")
    if isinstance(obj, (dict, list)):
        print(json.dumps(obj, indent=2))
    else:
        print(obj)


def main():
    now_ms = int(time.time() * 1000)
    rnd = random.randint(0, 999_999)

    email = f"aws_smoketest_{now_ms}_{rnd}@example.com"
    phone = f"+1999{now_ms % 10_000_000:07d}{rnd % 1_000:03d}"
    password = "Pass123!"

    # 1) Signup
    signup_body = {
        "email_address": email,
        "phone_number": phone,
        "name": "AWS Smoke Test User",
        "password": password,
    }
    resp = requests.post(f"{BASE}/v1/signup", json=signup_body, timeout=10)
    p("Signup status", resp.status_code)
    try:
        data = resp.json()
    except Exception:
        data = {"raw": resp.text}
    p("Signup body", data)
    resp.raise_for_status()
    user_id = data["user_id"]
    user_token = data["access_token"]

    # 2) Register device
    device_id = 600_000 + (rnd % 100_000)
    device_token = f"aws_dev_{now_ms}_{rnd}"
    sms_number = f"+1888{now_ms % 10_000_000:07d}{(rnd + 1) % 1_000:03d}"
    reg_body = {
        "device_id": device_id,
        "access_token": device_token,
        "sms_number": sms_number,
    }
    resp = requests.post(f"{BASE}/v1/registerDevice", json=reg_body, timeout=10)
    p("RegisterDevice status", resp.status_code)
    try:
        rb = resp.json()
    except Exception:
        rb = {"raw": resp.text}
    p("RegisterDevice body", rb)
    resp.raise_for_status()

    # 3) Link device to user (user token + pairing code in body)
    link_body = {"device_id": device_id, "access_token": device_token}
    headers = {"Access-Token": user_token}
    resp = requests.post(
        f"{BASE}/v1/registerDeviceToUser",
        headers=headers,
        params={"user_id": user_id},
        json=link_body,
        timeout=10,
    )
    p("RegisterDeviceToUser status", resp.status_code)
    try:
        lb = resp.json()
    except Exception:
        lb = {"raw": resp.text}
    p("RegisterDeviceToUser body", lb)
    resp.raise_for_status()

    # 4) Send one GPS sample
    now = datetime.datetime.now(datetime.timezone.utc)
    body = {
        "device_id": device_id,
        "latitude": -37.8136,
        "longitude": 144.9631,
        "timestamp": now.isoformat(),
    }
    headers = {"Access-Token": device_token}
    resp = requests.post(
        f"{BASE}/v1/sendGPSData", headers=headers, json=body, timeout=10
    )
    p("sendGPSData status", resp.status_code)
    try:
        sb = resp.json()
    except Exception:
        sb = {"raw": resp.text}
    p("sendGPSData body", sb)
    resp.raise_for_status()

    # 5) Fetch GPS data back via user API
    start = (now - datetime.timedelta(minutes=5)).isoformat()
    end = (now + datetime.timedelta(minutes=5)).isoformat()
    params = {
        "user_id": user_id,
        "device_id": device_id,
        "start_time": start,
        "end_time": end,
    }
    headers = {"Access-Token": user_token}
    resp = requests.get(
        f"{BASE}/v1/GPSData", headers=headers, params=params, timeout=10
    )
    p("GET /v1/GPSData status", resp.status_code)
    try:
        gb = resp.json()
    except Exception:
        gb = {"raw": resp.text}
    p("GET /v1/GPSData body", gb)
    resp.raise_for_status()

    print("\nAWS smoke test completed successfully.")


if __name__ == "__main__":
    main()

