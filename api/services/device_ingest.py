"""
Shared location ingest: persist GPS point, run geofence checks and notifications.
Used by HTTP sendGPSData and by device WebSocket location_update so both paths
behave the same (store + geofence + return data for broadcast).
Does not perform WebSocket broadcast; callers do that.
"""
import logging
import os
from datetime import datetime, timezone

from psycopg2 import connect

from api.db.devices import get_device, get_user_ids_for_device
from api.db.gps_data import add_gps_data
from api.db.geofences import get_geofences_by_user_id
from api.db.geofence_breaches import check_geofence_breaches
from api.db.models import GeofenceBreachEvent
from api.db.users import get_user
from api.notifications.geofence_breach_notifications import notify_geofence_breach_events
from api.notifications.sms_notifications import notify_geofence_breach_via_sms

logger = logging.getLogger(__name__)


def _parse_timestamp(value) -> datetime | None:
    """Parse timestamp from payload: ISO string, unix seconds, or unix ms."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.replace(tzinfo=value.tzinfo or timezone.utc)
    if isinstance(value, (int, float)):
        if value > 1e12:
            value = value / 1000.0
        return datetime.fromtimestamp(value, tz=timezone.utc)
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            pass
    return None


def ingest_location(
    device_id: int,
    payload: dict,
) -> tuple[dict, list[GeofenceBreachEvent]]:
    """
    Persist one GPS point and run geofence breach detection/notifications.
    Caller is responsible for broadcasting location_data and breach events.

    :param device_id: Device ID (must match payload if present).
    :param payload: Dict with latitude, longitude; optional: timestamp, speed, heading,
                    trip_active, current_draw, voltage.
    :return: (location_data dict for broadcast_location_update, list of breach events).
    """
    lat = payload.get("latitude")
    lon = payload.get("longitude")
    if lat is None or lon is None:
        raise ValueError("latitude and longitude are required")

    latitude = float(lat)
    longitude = float(lon)
    ts = _parse_timestamp(payload.get("timestamp")) or datetime.now(timezone.utc)
    if ts.year < 2020:
        ts = datetime.now(timezone.utc)

    speed = payload.get("speed")
    if speed is not None:
        speed = float(speed)
    heading = payload.get("heading")
    if heading is not None:
        heading = float(heading)
    trip_active = payload.get("trip_active")
    if trip_active is not None and not isinstance(trip_active, bool):
        trip_active = bool(trip_active)
    current_draw = payload.get("current_draw")
    if current_draw is not None:
        current_draw = float(current_draw)
    voltage = payload.get("voltage")
    if voltage is not None:
        voltage = float(voltage)

    db_conn = connect(dsn=os.getenv("DATABASE_URI"))
    try:
        add_gps_data(
            db_conn=db_conn,
            device_id=device_id,
            timestamp=ts,
            latitude=latitude,
            longitude=longitude,
            speed=speed,
            heading=heading,
            trip_active=trip_active,
        )

        user_ids = get_user_ids_for_device(db_conn, device_id)
        all_breach_events: list[GeofenceBreachEvent] = []

        for user_id in user_ids:
            geofences = get_geofences_by_user_id(db_conn, user_id)
            breach_events = check_geofence_breaches(
                db_conn=db_conn,
                device_id=device_id,
                user_id=user_id,
                latitude=latitude,
                longitude=longitude,
                geofences=geofences,
            )
            if breach_events:
                user = get_user(db_conn, user_id)
                device = get_device(db_conn, device_id)
                geofences_by_id = {g.geofence_id: g for g in geofences}
                notify_geofence_breach_events(
                    db_conn=db_conn,
                    events=breach_events,
                    user=user,
                    device=device,
                    geofences_by_id=geofences_by_id,
                )
                notify_geofence_breach_via_sms(
                    db_conn=db_conn,
                    events=breach_events,
                    user=user,
                    device=device,
                    geofences_by_id=geofences_by_id,
                )
            all_breach_events.extend(breach_events)

        if all_breach_events:
            logger.info(
                f"GPS data triggered {len(all_breach_events)} geofence breach(es) for device {device_id}"
            )

        location_data = {
            "device_id": device_id,
            "latitude": latitude,
            "longitude": longitude,
            "speed": speed,
            "heading": heading,
            "created_at": ts.isoformat(),
        }
        if current_draw is not None:
            location_data["current_draw"] = current_draw
        if voltage is not None:
            location_data["voltage"] = voltage

        return (location_data, all_breach_events)
    finally:
        db_conn.close()
