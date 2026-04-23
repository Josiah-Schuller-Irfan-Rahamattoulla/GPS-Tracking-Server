"""
Unit tests for shared device ingest (ingest_location).
Validation tests run without DB; full ingest is covered by test_device_flows integration tests.
"""
import pytest
from datetime import datetime, timezone

from api.db.gps_data import add_gps_data
from api.services.device_ingest import ingest_location


def test_ingest_location_requires_latitude_longitude():
    """ingest_location raises ValueError when latitude or longitude is missing."""
    with pytest.raises(ValueError, match="latitude and longitude are required"):
        ingest_location(1, {})
    with pytest.raises(ValueError, match="latitude and longitude are required"):
        ingest_location(1, {"latitude": 52.0})
    with pytest.raises(ValueError, match="latitude and longitude are required"):
        ingest_location(1, {"longitude": 0.0})


class _FakeCursor:
    def __init__(self):
        self.executed = []
        self._fetch_index = 0

    def execute(self, sql, params=None):
        self.executed.append((sql, params))

    def fetchall(self):
        if self._fetch_index == 0:
            self._fetch_index += 1
            return [("device_id",), ("time",), ("latitude",), ("longitude",)]
        return []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _FakeConnection:
    def __init__(self):
        self.cursor_obj = _FakeCursor()

    def cursor(self):
        return self.cursor_obj

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_add_gps_data_omits_missing_optional_columns():
    """add_gps_data should work on older schemas that lack speed/heading/trip_active."""
    conn = _FakeConnection()

    add_gps_data(
        db_conn=conn,
        device_id=7,
        timestamp=datetime.now(timezone.utc),
        latitude=51.5,
        longitude=-0.1,
        speed=42.0,
        heading=180.0,
        trip_active=True,
    )

    insert_sql, insert_params = conn.cursor_obj.executed[-1]
    assert "speed" not in insert_sql.lower()
    assert "heading" not in insert_sql.lower()
    assert "trip_active" not in insert_sql.lower()
    assert len(insert_params) == 4
