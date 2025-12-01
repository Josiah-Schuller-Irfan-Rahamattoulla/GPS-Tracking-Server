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
                """,
                (user_id,),
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
            cursor.execute(
                "SELECT * FROM devices WHERE device_id = %s",
                (device_id,),
            )
            device = cursor.fetchone()
            return Device(**device) if device else None


def create_device(
    db_conn: PGConnection,
    device_id: int,
    access_token: str,
    sms_number: str,
    name: str | None = None,
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
    :param name: User-friendly device name (optional)
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
                INSERT INTO devices (device_id, access_token, sms_number, name, control_1, control_2, control_3, control_4)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING *
                """,
                (
                    device_id,
                    access_token,
                    sms_number,
                    name,
                    control_1,
                    control_2,
                    control_3,
                    control_4,
                ),
            )


def create_user_device_row(db_conn: PGConnection, user_id: int, device_id: int) -> None:
    """
    Create a row in the users_devices table to link a user and a device.
    If the link already exists, this is a no-op (handles duplicate registration gracefully).

    :param db_conn: Database connection object
    :param user_id: ID of the user
    :param device_id: ID of the device
    """
    with db_conn:
        with db_conn.cursor() as cursor:
            # Use ON CONFLICT DO NOTHING to handle duplicate links gracefully
            # PRIMARY KEY is on (user_id, device_id), so ON CONFLICT will catch duplicates
            cursor.execute(
                """
                INSERT INTO users_devices (user_id, device_id) 
                VALUES (%s, %s)
                ON CONFLICT (user_id, device_id) DO NOTHING
                """,
                (user_id, device_id),
            )


def get_device_by_user(db_conn: PGConnection, device_id: int, user_id: int) -> Device | None:
    """
    Retrieve a device and verify it belongs to the user.

    :param db_conn: Database connection object
    :param device_id: ID of the device
    :param user_id: ID of the user
    :return: Device if found and owned by user, None otherwise
    """
    with db_conn:
        with db_conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                """
                SELECT d.* FROM devices d
                JOIN users_devices ud ON d.device_id = ud.device_id
                WHERE d.device_id = %s AND ud.user_id = %s
                """,
                (device_id, user_id),
            )
            device = cursor.fetchone()
            return Device(**device) if device else None


def update_device_controls(
    db_conn: PGConnection,
    device_id: int,
    user_id: int,
    control_1: bool | None = None,
    control_2: bool | None = None,
    control_3: bool | None = None,
    control_4: bool | None = None,
    expected_version: int | None = None,
) -> Device | None:
    """
    Update device control flags with optimistic locking.

    :param db_conn: Database connection object
    :param device_id: ID of the device
    :param user_id: ID of the user (for verification)
    :param control_1: Control 1 state (optional)
    :param control_2: Control 2 state (optional)
    :param control_3: Control 3 state (optional)
    :param control_4: Control 4 state (optional)
    :param expected_version: Expected control_version for optimistic locking (optional)
    :return: Updated Device if successful, None if not found or version conflict
    """
    with db_conn:
        with db_conn.cursor(cursor_factory=RealDictCursor) as cursor:
            # First verify device belongs to user and get current state
            cursor.execute(
                """
                SELECT d.* FROM devices d
                JOIN users_devices ud ON d.device_id = ud.device_id
                WHERE d.device_id = %s AND ud.user_id = %s
                """,
                (device_id, user_id),
            )
            device_row = cursor.fetchone()
            if not device_row:
                return None
            
            device = Device(**device_row)
            
            # Check version if provided (optimistic locking)
            if expected_version is not None:
                current_version = device.control_version if device.control_version is not None else 0
                if current_version != expected_version:
                    return None  # Version conflict
            
            # Build update query
            updates = []
            values = []
            
            if control_1 is not None:
                updates.append("control_1 = %s")
                values.append(control_1)
            if control_2 is not None:
                updates.append("control_2 = %s")
                values.append(control_2)
            if control_3 is not None:
                updates.append("control_3 = %s")
                values.append(control_3)
            if control_4 is not None:
                updates.append("control_4 = %s")
                values.append(control_4)
            
            if not updates:
                return device  # No updates, return existing
            
            # Increment version and update timestamp
            updates.append("control_version = COALESCE(control_version, 0) + 1")
            updates.append("controls_updated_at = CURRENT_TIMESTAMP")
            
            # Build WHERE clause
            where_parts = ["d.device_id = ud.device_id", "d.device_id = %s", "ud.user_id = %s"]
            values.extend([device_id, user_id])
            
            # Add version check to WHERE clause if provided
            if expected_version is not None:
                where_parts.append("d.control_version = %s")
                values.append(expected_version)
            
            cursor.execute(
                f"""
                UPDATE devices d
                SET {', '.join(updates)}
                FROM users_devices ud
                WHERE {' AND '.join(where_parts)}
                RETURNING d.*
                """,
                values,
            )
            updated = cursor.fetchone()
            return Device(**updated) if updated else None
