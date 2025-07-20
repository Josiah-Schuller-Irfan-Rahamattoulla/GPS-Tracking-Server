from datetime import datetime

from psycopg2.extensions import connection as PGConnection
from psycopg2.extras import RealDictCursor

from db.models import GPSData


def add_gps_data(
    db_conn: PGConnection,
    device_id: int,
    timestamp: datetime,
    latitude: float,
    longitude: float,
):
    """
    Add GPS data to the database.

    :param device_id: ID of the device sending the GPS data
    :param timestamp: Timestamp of the GPS data
    :param latitude: Latitude of the GPS data
    :param longitude: Longitude of the GPS data
    """
    with db_conn:
        with db_conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO gps_data (device_id, time, latitude, longitude) VALUES (%s, %s, %s, %s)",
                (device_id, timestamp, latitude, longitude),
            )


def get_gps_data(db_conn: PGConnection, device_id: int, start_time: datetime, end_time: datetime):
    """
    Retrieve GPS data for a specific device within a time range.

    :param db_conn: Database connection object
    :param device_id: ID of the device to retrieve GPS data for
    :param start_time: Start of the time range
    :param end_time: End of the time range
    :return: List of GPS data records
    """
    with db_conn:
        with db_conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                "SELECT * FROM gps_data WHERE device_id = %s AND time >= %s AND time < %s",
                (device_id, start_time, end_time),
            )
            records = cursor.fetchall()
            return [GPSData(**record) for record in records] if records else []
