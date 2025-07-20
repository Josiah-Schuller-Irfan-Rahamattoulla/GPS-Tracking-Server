from psycopg2.extensions import connection as PGConnection
from psycopg2.extras import RealDictCursor

from db.models import User


def get_user(db_conn: PGConnection, user_id: int) -> User | None:
    """
    Retrieve a user from the database by their ID.

    :param user_id: ID of the user to retrieve
    :param db_conn: Database connection object
    :return: User data if found, None otherwise
    """
    with db_conn:
        with db_conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
            row = cursor.fetchone()
            return User(**row) if row else None
