"""
Geofence breach detection and event logging.
Handles detection of devices entering/exiting geofences and logging breach events.
"""
import logging
from datetime import datetime, timezone
from math import radians, cos, sin, asin, sqrt

from psycopg2.extensions import connection as PGConnection
from psycopg2.extras import RealDictCursor

from db.models import Geofence, GeofenceBreachEvent

logger = logging.getLogger(__name__)


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great circle distance in meters between two points
    on the earth (specified in decimal degrees).
    
    :param lat1: Latitude of point 1
    :param lon1: Longitude of point 1
    :param lat2: Latitude of point 2
    :param lon2: Longitude of point 2
    :return: Distance in meters
    """
    # Convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

    # Haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * asin(sqrt(a))
    
    # Radius of earth in meters
    r = 6371000
    return c * r


def is_point_in_geofence(
    point_lat: float,
    point_lon: float,
    geofence: Geofence
) -> bool:
    """
    Check if a point is within a geofence circle.
    
    :param point_lat: Latitude of the point to check
    :param point_lon: Longitude of the point to check
    :param geofence: Geofence object with center coordinates and radius
    :return: True if point is inside geofence, False otherwise
    """
    distance = haversine_distance(
        point_lat, point_lon,
        geofence.latitude, geofence.longitude
    )
    return distance <= geofence.radius


def get_last_breach_event(
    db_conn: PGConnection,
    device_id: int,
    geofence_id: int
) -> GeofenceBreachEvent | None:
    """
    Get the most recent breach event for a device and geofence combination.
    
    :param db_conn: Database connection
    :param device_id: Device ID
    :param geofence_id: Geofence ID
    :return: Most recent GeofenceBreachEvent or None
    """
    with db_conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(
            """
            SELECT * FROM geofence_breach_events
            WHERE device_id = %s AND geofence_id = %s
            ORDER BY event_time DESC
            LIMIT 1
            """,
            (device_id, geofence_id)
        )
        event = cursor.fetchone()
        return GeofenceBreachEvent(**event) if event else None


def log_breach_event(
    db_conn: PGConnection,
    device_id: int,
    geofence_id: int,
    user_id: int,
    event_type: str,
    latitude: float,
    longitude: float
) -> GeofenceBreachEvent:
    """
    Log a geofence breach event to the database.
    
    :param db_conn: Database connection
    :param device_id: Device ID
    :param geofence_id: Geofence ID
    :param user_id: User ID who owns the geofence
    :param event_type: 'ENTERED' or 'EXITED'
    :param latitude: Latitude where breach occurred
    :param longitude: Longitude where breach occurred
    :return: Created GeofenceBreachEvent object
    """
    with db_conn:
        with db_conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                """
                INSERT INTO geofence_breach_events 
                (device_id, geofence_id, user_id, event_type, latitude, longitude, event_time)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING *
                """,
                (device_id, geofence_id, user_id, event_type, latitude, longitude, 
                 datetime.now(timezone.utc))
            )
            event = cursor.fetchone()
            logger.info(
                f"Geofence breach logged: device={device_id}, geofence={geofence_id}, "
                f"type={event_type}, lat={latitude:.6f}, lon={longitude:.6f}"
            )
            return GeofenceBreachEvent(**event)


def check_geofence_breaches(
    db_conn: PGConnection,
    device_id: int,
    user_id: int,
    latitude: float,
    longitude: float,
    geofences: list[Geofence]
) -> list[GeofenceBreachEvent]:
    """
    Check if a GPS point triggers any geofence breaches (enter/exit).
    Compares current position against all active geofences and detects state transitions.
    
    :param db_conn: Database connection
    :param device_id: Device ID
    :param user_id: User ID who owns the geofences
    :param latitude: Current GPS latitude
    :param longitude: Current GPS longitude
    :param geofences: List of active geofences to check
    :return: List of new GeofenceBreachEvent objects created
    """
    breach_events = []
    
    for geofence in geofences:
        if not geofence.enabled:
            continue
            
        # Check if device is currently inside geofence
        is_inside = is_point_in_geofence(latitude, longitude, geofence)
        
        # Get last breach event for this device/geofence combination
        last_event = get_last_breach_event(db_conn, device_id, geofence.geofence_id)
        
        # Determine if state changed
        if last_event is None:
            # First time seeing this device - log entry if inside
            if is_inside:
                event = log_breach_event(
                    db_conn, device_id, geofence.geofence_id, user_id,
                    'ENTERED', latitude, longitude
                )
                breach_events.append(event)
        else:
            # Check for state transition
            was_inside = last_event.event_type == 'ENTERED'
            
            if is_inside and not was_inside:
                # Device entered geofence
                event = log_breach_event(
                    db_conn, device_id, geofence.geofence_id, user_id,
                    'ENTERED', latitude, longitude
                )
                breach_events.append(event)
            elif not is_inside and was_inside:
                # Device exited geofence
                event = log_breach_event(
                    db_conn, device_id, geofence.geofence_id, user_id,
                    'EXITED', latitude, longitude
                )
                breach_events.append(event)
    
    return breach_events


def mark_breach_notification_sent(
    db_conn: PGConnection,
    event_id: int,
    notification_type: str,
    sent_at: datetime | None = None
) -> None:
    """
    Mark a geofence breach event as having a notification sent.
    
    :param db_conn: Database connection
    :param event_id: GeofenceBreachEvent ID
    :param notification_type: 'EMAIL' or 'SMS'
    :param sent_at: Timestamp when notification was sent
    """
    if sent_at is None:
        sent_at = datetime.now(timezone.utc)
    
    # Store notification audit in a table if it exists, otherwise just log
    try:
        with db_conn:
            with db_conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO notification_audit_log 
                    (event_id, notification_type, sent_at)
                    VALUES (%s, %s, %s)
                    """,
                    (event_id, notification_type, sent_at)
                )
                logger.debug(f"Marked {notification_type} notification sent for event {event_id}")
    except Exception as e:
        logger.warning(f"Could not record notification audit: {e}")
