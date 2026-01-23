from psycopg2.extensions import connection as PGConnection
from psycopg2.extras import RealDictCursor

from db.models import Geofence


def get_geofences_by_user_id(db_conn: PGConnection, user_id: int) -> list[Geofence]:
    """
    Retrieve all geofences for a user from the database.

    :param db_conn: Database connection object
    :param user_id: ID of the user to retrieve geofences for
    :return: List of Geofence objects for the user
    """
    with db_conn:
        with db_conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                "SELECT * FROM geofences WHERE user_id = %s ORDER BY created_at DESC",
                (user_id,),
            )
            geofences = cursor.fetchall()
            return [Geofence(**gf) for gf in geofences] if geofences else []


def get_geofence(db_conn: PGConnection, geofence_id: int) -> Geofence | None:
    """
    Retrieve a geofence from the database by its ID.

    :param db_conn: Database connection object
    :param geofence_id: ID of the geofence to retrieve
    :return: Geofence data if found, None otherwise
    """
    with db_conn:
        with db_conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                "SELECT * FROM geofences WHERE geofence_id = %s",
                (geofence_id,),
            )
            geofence = cursor.fetchone()
            return Geofence(**geofence) if geofence else None


def create_geofence(
    db_conn: PGConnection,
    user_id: int,
    name: str,
    latitude: float,
    longitude: float,
    radius: float = 100.0,
    enabled: bool = True,
) -> Geofence:
    """
    Create a new geofence in the database.

    :param db_conn: Database connection object
    :param user_id: ID of the user who owns this geofence
    :param name: Display name for the geofence
    :param latitude: Center latitude coordinate
    :param longitude: Center longitude coordinate
    :param radius: Radius in meters (default 100)
    :param enabled: Whether geofence is active (default True)
    :return: Created Geofence object
    """
    with db_conn:
        with db_conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                """
                INSERT INTO geofences (user_id, name, latitude, longitude, radius, enabled)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING *
                """,
                (user_id, name, latitude, longitude, radius, enabled),
            )
            geofence = cursor.fetchone()
            return Geofence(**geofence)


def update_geofence(
    db_conn: PGConnection,
    geofence_id: int,
    user_id: int,
    name: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    radius: float | None = None,
    enabled: bool | None = None,
) -> Geofence | None:
    """
    Update an existing geofence in the database. Verifies user owns the geofence.

    :param db_conn: Database connection object
    :param geofence_id: ID of the geofence to update
    :param user_id: ID of the user (for verification)
    :param name: New name (optional)
    :param latitude: New latitude (optional)
    :param longitude: New longitude (optional)
    :param radius: New radius (optional)
    :param enabled: New enabled state (optional)
    :return: Updated Geofence object, or None if not found or not owned by user
    """
    # Build dynamic update query
    updates = []
    values = []
    
    if name is not None:
        updates.append("name = %s")
        values.append(name)
    if latitude is not None:
        updates.append("latitude = %s")
        values.append(latitude)
    if longitude is not None:
        updates.append("longitude = %s")
        values.append(longitude)
    if radius is not None:
        updates.append("radius = %s")
        values.append(radius)
    if enabled is not None:
        updates.append("enabled = %s")
        values.append(enabled)
    
    if not updates:
        # No updates, just verify ownership and return existing
        geofence = get_geofence(db_conn, geofence_id)
        if geofence and geofence.user_id == user_id:
            return geofence
        return None
    
    values.extend([geofence_id, user_id])
    
    with db_conn:
        with db_conn.cursor(cursor_factory=RealDictCursor) as cursor:
            set_clause = ', '.join(updates)
            query = f"UPDATE geofences SET {set_clause} WHERE geofence_id = %s AND user_id = %s RETURNING *"
            cursor.execute(query, values)
            geofence = cursor.fetchone()
            return Geofence(**geofence) if geofence else None


def delete_geofence(db_conn: PGConnection, geofence_id: int, user_id: int) -> bool:
    """
    Delete a geofence from the database. Verifies user owns the geofence.

    :param db_conn: Database connection object
    :param geofence_id: ID of the geofence to delete
    :param user_id: ID of the user (for verification)
    :return: True if deleted, False if not found or not owned by user
    """
    with db_conn:
        with db_conn.cursor() as cursor:
            cursor.execute(
                "DELETE FROM geofences WHERE geofence_id = %s AND user_id = %s",
                (geofence_id, user_id),
            )
            return cursor.rowcount > 0

