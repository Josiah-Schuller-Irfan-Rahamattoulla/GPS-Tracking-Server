#!/usr/bin/env python3
"""
Quick tests for the /v1/cell_location endpoint.
Runs several POST variants and prints status, body and timing.
"""
import argparse
import json
import time
import requests


def do_post(url, headers, payload, name):
    print(f"Test: {name}")
    print("  headers:", headers)
    print("  payload:", json.dumps(payload))
    start = time.time()
    try:
        r = requests.post(url, headers=headers, json=payload, timeout=15, verify=False)
        elapsed = time.time() - start
        print(f"  -> {r.status_code} in {elapsed:.3f}s")
        try:
            print("  body:", r.json())
        except Exception:
            print("  body (text):", r.text[:500])
    except Exception as e:
        elapsed = time.time() - start
        print(f"  Exception after {elapsed:.3f}s: {e}")
    print()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://chatty-otter-15.loca.lt", help="Base URL of API")
    parser.add_argument("--device-id", type=int, default=67)
    parser.add_argument("--device-token", default="sim_device_12345_123456789")
    parser.add_argument("--user-token", default="test_user_token")
    args = parser.parse_args()

    url = f"{args.base_url}/v1/cell_location"

    payload = {
        "cells": [{
            "cellId": 137713153,
            "mcc": 505,
            "mnc": 1,
            "lac": 12385,
            "tac": 12385,
            "signal": 34
        }],
        "device_id": args.device_id
    }

    # Variant A: correct device token header
    headers_a = {"Content-Type": "application/json", "Access-Token": args.device_token}
    do_post(url, headers_a, payload, "Device token (expected) ")

    # Variant B: missing Access-Token
    headers_b = {"Content-Type": "application/json"}
    do_post(url, headers_b, payload, "No token (expected 401/403)")

    # Variant C: user token in Access-Token
    headers_c = {"Content-Type": "application/json", "Access-Token": args.user_token}
    do_post(url, headers_c, payload, "User token in Access-Token")

    # Variant D: include bypass header like firmware
    headers_d = {"Content-Type": "application/json", "Access-Token": args.device_token, "Bypass-Tunnel-Reminder": "1"}
    do_post(url, headers_d, payload, "Device token + bypass header")

    # Variant E: wrong content-type
    headers_e = {"Content-Type": "text/plain", "Access-Token": args.device_token}
    do_post(url, headers_e, payload, "Wrong content-type")

    # Variant F: Large payload
    big_payload = {"cells": [payload["cells"][0]] * 200, "device_id": args.device_id}
    headers_f = {"Content-Type": "application/json", "Access-Token": args.device_token}
    do_post(url, headers_f, big_payload, "Large payload (200 cells)")


if __name__ == "__main__":
    main()
