from datetime import datetime

from psycopg2.extensions import connection as PC2Connection


def add_gps_data(
    db_conn: PC2Connection,
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
                (device_id, timestamp, latitude, longitude)
            )
