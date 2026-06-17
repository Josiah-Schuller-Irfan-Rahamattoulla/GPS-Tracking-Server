import os

import pytest
import requests


def _base_url() -> str:
    return os.getenv("TEST_BASE_URL", "http://localhost:8000").rstrip("/")


def _create_user(base: str) -> tuple[int, str]:
    ts = __import__("time").time_ns()
    user = {
        "email_address": f"pgps_test_{ts}@example.com",
        "phone_number": f"+1555{ts % 10_000_000_000:010d}",
        "name": "P-GPS Test User",
        "password": "SecurePass123!",
    }
    r = requests.post(f"{base}/v1/signup", json=user, timeout=10)
    r.raise_for_status()
    data = r.json()
    return int(data["user_id"]), str(data["access_token"])


def _create_and_link_device(base: str, user_id: int, user_token: str) -> tuple[int, str]:
    ts = __import__("time").time_ns()
    device = {
        "device_id": int(910_000_000 + (ts % 50_000_000)),
        "access_token": f"pgps_device_token_{ts}",
        "sms_number": f"+1666{ts % 10_000_000_000:010d}",
        "name": "P-GPS Test Device",
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


def test_pgps_endpoint_returns_binary_data():
    """
    Smoke test: /v1/pgps returns binary P-GPS data from nRF Cloud (via server proxy).

  Skips when nRF Cloud Location credentials are not configured (503).
    """
    base = _base_url()
    url = f"{base}/v1/pgps"

    try:
        user_id, user_token = _create_user(base)
        device_id, device_token = _create_and_link_device(base, user_id, user_token)
        r = requests.get(
            url,
            params={
                "device_id": device_id,
                "prediction_count": 8,
                "prediction_period_min": 120,
            },
            headers={"Access-Token": device_token},
            timeout=60,
        )
    except requests.exceptions.ConnectionError:
        pytest.skip("Server not reachable")

    if r.status_code == 503:
        pytest.skip(
            "P-GPS provider unavailable (expected if NRFCLOUD_OAT / org+project slugs "
            "are not configured in the deployed environment)"
        )

    assert r.status_code == 200, f"{r.status_code}: {r.text[:300]}"
    assert r.headers.get("Content-Type", "").startswith("application/octet-stream")
    assert r.headers.get("X-PGPS-Source") == "nRF Cloud"
    # 8 predictions ~= 16 KB plus header; reject empty/tiny error bodies.
    assert len(r.content) >= 2048, f"Unexpectedly small P-GPS payload: {len(r.content)} bytes"
