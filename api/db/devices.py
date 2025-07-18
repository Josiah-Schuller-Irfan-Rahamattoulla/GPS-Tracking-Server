from psycopg2.extensions import connection as PC2Connection
from psycopg2.extras import RealDictCursor

from db.models import Device


def get_device(db_conn: PC2Connection, device_id: int):
    """
    Retrieve a device from the database by its ID.

    :param device_id: ID of the device to retrieve
    :param db_conn: Database connection object
    :return: Device data if found, None otherwise
    """
    with db_conn:
        with db_conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("SELECT * FROM devices WHERE device_id = %s", (device_id,))
            device = cursor.fetchone()
            return Device(**device) if device else None
