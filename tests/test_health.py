import os

import requests


def _base_url() -> str:
    return os.getenv("TEST_BASE_URL", "http://localhost:8000")


def test_health_check():
    response = requests.get(f"{_base_url()}/health", timeout=10)
    response.raise_for_status()
    payload = response.json()
    assert payload.get("status") == "healthy"
