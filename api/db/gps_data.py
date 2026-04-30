from datetime import datetime

from psycopg2.extensions import connection as PGConnection
from psycopg2.extras import RealDictCursor

from api.db.models import GPSData


_gps_data_columns_cache: set[str] | None = None


def _get_gps_data_columns(db_conn: PGConnection) -> set[str]:
    """
    Return available columns in gps_data table (cached).

    Production DBs may lag behind migrations; this allows the API to degrade
    gracefully if optional columns (speed/heading/trip_active) are missing.
    """
    global _gps_data_columns_cache
    if _gps_data_columns_cache is not None:
        return _gps_data_columns_cache

    with db_conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'gps_data'
            """
        )
        _gps_data_columns_cache = {row["column_name"] for row in cursor.fetchall()}
    return _gps_data_columns_cache


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
        cols = _get_gps_data_columns(db_conn)

        insert_cols: list[str] = ["device_id", "time", "latitude", "longitude"]
        values: list[object] = [device_id, timestamp, latitude, longitude]

        if "speed" in cols:
            insert_cols.append("speed")
            values.append(speed)
        if "heading" in cols:
            insert_cols.append("heading")
            values.append(heading)
        if "trip_active" in cols:
            insert_cols.append("trip_active")
            values.append(trip_active)

        placeholders = ", ".join(["%s"] * len(insert_cols))
        columns_sql = ", ".join(insert_cols)
        query = f"INSERT INTO gps_data ({columns_sql}) VALUES ({placeholders})"

        with db_conn.cursor() as cursor:
            cursor.execute(query, tuple(values))


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
