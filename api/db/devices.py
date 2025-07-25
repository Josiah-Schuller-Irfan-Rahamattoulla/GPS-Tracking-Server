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
                """, (user_id,),
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
            cursor.execute("SELECT * FROM devices WHERE device_id = %s", (device_id,),)
            device = cursor.fetchone()
            return Device(**device) if device else None
        

def create_device(
    db_conn: PGConnection,
    device_id: int,
    access_token: str,
    sms_number: str,
    control_1: bool | None = None,
    control_2: bool | None = None,
    control_3: bool | None = None,
    control_4: bool | None = None,
) -> None:
    """
    Create a new device in the database.

    :param db_conn: Database connection object
    :param device_id: ID of the device to create
    :param access_token: Access token for the device
    :param sms_number: SMS number associated with the device
    :param control_1: Control 1 state (optional)
    :param control_2: Control 2 state (optional)
    :param control_3: Control 3 state (optional)
    :param control_4: Control 4 state (optional)
    :return: None
    """
    with db_conn:
        with db_conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                """
                INSERT INTO devices (device_id, access_token, sms_number, control_1, control_2, control_3, control_4)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING *
                """,
                (device_id, access_token, sms_number, control_1, control_2, control_3, control_4,),
            )


def create_user_device_row(db_conn: PGConnection, user_id: int, device_id: int) -> None:
    """
    Create a row in the users_devices table to link a user and a device.

    :param db_conn: Database connection object
    :param user_id: ID of the user
    :param device_id: ID of the device
    """
    with db_conn:
        with db_conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO users_devices (user_id, device_id) VALUES (%s, %s)",
                (user_id, device_id,),
            )
