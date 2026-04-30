import os

import pytest
import requests


def _base_url() -> str:
    return os.getenv("TEST_BASE_URL", "http://localhost:8000").rstrip("/")


def _create_user(base: str) -> tuple[int, str]:
    ts = __import__("time").time_ns()
    user = {
        "email_address": f"agnss_test_{ts}@example.com",
        "phone_number": f"+1555{ts % 10_000_000_000:010d}",
        "name": "A-GNSS Test User",
        "password": "SecurePass123!",
    }
    r = requests.post(f"{base}/v1/signup", json=user, timeout=10)
    r.raise_for_status()
    data = r.json()
    return int(data["user_id"]), str(data["access_token"])


def _create_and_link_device(base: str, user_id: int, user_token: str) -> tuple[int, str]:
    ts = __import__("time").time_ns()
    device = {
        "device_id": int(900_000_000 + (ts % 50_000_000)),
        "access_token": f"agnss_device_token_{ts}",
        "sms_number": f"+1666{ts % 10_000_000_000:010d}",
        "name": "A-GNSS Test Device",
    }

    r = requests.post(f"{base}/v1/registerDevice", json=device, timeout=10)
    r.raise_for_status()

    link = requests.post(
        f"{base}/v1/registerDeviceToUser",
        headers={"Access-Token": user_token},
        params={"user_id": user_id},
        json={"device_id": device["device_id"], "access_token": device["access_token"]},
        timeout=10,
    )
    link.raise_for_status()

    return int(device["device_id"]), str(device["access_token"])


def test_agnss_endpoint_returns_binary_data():
    """
    Smoke test: /v1/agnss returns binary A-GNSS data.

    Creates a fresh user+device so the test does not depend on pre-seeded DB state.
    """
    base = _base_url()
    url = f"{base}/v1/agnss"

    try:
        user_id, user_token = _create_user(base)
        device_id, device_token = _create_and_link_device(base, user_id, user_token)
        r = requests.get(
            url,
            # Use cell ID hints to exercise the "proper" filtered ephemeris request path.
            # Values don't need to be real for a smoke test (server may ignore/return default),
            # but they must be structurally valid.
            params={"device_id": device_id, "mcc": 505, "mnc": 1, "tac": 1, "eci": 1},
            headers={"Access-Token": device_token},
            timeout=30,
        )
    except requests.exceptions.ConnectionError:
        pytest.skip("Server not reachable")

    if r.status_code == 503:
        pytest.skip(
            "A-GNSS provider unavailable (expected if NRFCLOUD_OAT / org+project slugs "
            "are not configured in the deployed environment)"
        )

    assert r.status_code == 200, f"{r.status_code}: {r.text[:300]}"
    # A-GNSS payload should be binary and non-trivial in size.
    assert len(r.content) >= 512, f"Unexpectedly small A-GNSS payload: {len(r.content)} bytes"
