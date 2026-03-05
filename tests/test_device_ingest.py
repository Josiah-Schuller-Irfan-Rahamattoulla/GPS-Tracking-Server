"""
Unit tests for shared device ingest (ingest_location).
Validation tests run without DB; full ingest is covered by test_device_flows integration tests.
"""
import pytest

from api.services.device_ingest import ingest_location


def test_ingest_location_requires_latitude_longitude():
    """ingest_location raises ValueError when latitude or longitude is missing."""
    with pytest.raises(ValueError, match="latitude and longitude are required"):
        ingest_location(1, {})
    with pytest.raises(ValueError, match="latitude and longitude are required"):
        ingest_location(1, {"latitude": 52.0})
    with pytest.raises(ValueError, match="latitude and longitude are required"):
        ingest_location(1, {"longitude": 0.0})
