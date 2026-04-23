from datetime import datetime

from psycopg2.extensions import connection as PGConnection
from psycopg2.extras import RealDictCursor

from api.db.models import GPSData


def add_gps_data(
    db_conn: PGConnection,
    device_id: int,
    timestamp: datetime,
    latitude: float,
    longitude: float,
    speed: float | None = None,
    heading: float | None = None,
    trip_active: bool | None = None,
):
    """
    Add GPS data to the database.

    :param device_id: ID of the device sending the GPS data
    :param timestamp: Timestamp of the GPS data
    :param latitude: Latitude of the GPS data
    :param longitude: Longitude of the GPS data
    :param speed: Vehicle speed in km/h (optional)
    :param heading: Compass heading in degrees 0-360 (optional)
    :param trip_active: Hardware IMU-detected trip status (optional)
    """
    with db_conn:
        with db_conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_schema = 'public' AND table_name = 'gps_data'
                """
            )
            available_columns = {row[0] for row in cursor.fetchall()}

            columns = ["device_id", "time", "latitude", "longitude"]
            values = [device_id, timestamp, latitude, longitude]

            optional_columns = {
                "speed": speed,
                "heading": heading,
                "trip_active": trip_active,
            }

            for column_name, value in optional_columns.items():
                if column_name in available_columns:
                    columns.append(column_name)
                    values.append(value)

            placeholders = ", ".join(["%s"] * len(columns))
            columns_sql = ", ".join(columns)
            cursor.execute(
                f"""
                INSERT INTO gps_data ({columns_sql})
                VALUES ({placeholders})
                """,
                tuple(values),
            )


def get_gps_data(
    db_conn: PGConnection,
    device_id: int,
    start_time: datetime,
    end_time: datetime,
):
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
