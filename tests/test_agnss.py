import os

import pytest
import requests


def _base_url() -> str:
    return os.getenv("TEST_BASE_URL", "http://localhost:8000").rstrip("/")


def _device_id() -> int:
    return int(os.getenv("TEST_DEVICE_ID", "67"))


def _device_token() -> str:
    return os.getenv("TEST_DEVICE_TOKEN", "sim_device_12345_123456789")


def test_agnss_endpoint_returns_binary_data():
    """
    Smoke test: /v1/agnss returns binary A-GNSS data.

    Uses TEST_BASE_URL, TEST_DEVICE_ID, TEST_DEVICE_TOKEN for flexibility.
    """
    base = _base_url()
    url = f"{base}/v1/agnss"
    params = {"device_id": _device_id()}
    headers = {"Access-Token": _device_token()}

    try:
        r = requests.get(url, params=params, headers=headers, timeout=20)
    except requests.exceptions.ConnectionError:
        pytest.skip("Server not reachable")

    assert r.status_code == 200, f"{r.status_code}: {r.text[:300]}"
    # A-GNSS payload should be binary and non-trivial in size.
    assert len(r.content) >= 512, f"Unexpectedly small A-GNSS payload: {len(r.content)} bytes"
