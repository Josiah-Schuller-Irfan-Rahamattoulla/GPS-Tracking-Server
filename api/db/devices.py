from psycopg2.extensions import connection as PGConnection
from psycopg2.extras import RealDictCursor

from db.models import Device


def get_devices_by_user_id(db_conn: PGConnection, user_id: int) -> list[Device]:
    """
    Retrieve devices associated with a user from the database.

    :param db_conn: Database connection object
    :param user_id: ID of the user to retrieve devices for
    :return: List of Device objects associated with the user
    """
    with db_conn:
        with db_conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                """
                SELECT * FROM devices
                JOIN users_devices ON devices.device_id = users_devices.device_id
                WHERE users_devices.user_id = %s
                """, (user_id,)
            )
            devices = cursor.fetchall()
            return [Device(**device) for device in devices] if devices else []


def get_device(db_conn: PGConnection, device_id: int) -> Device | None:
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
