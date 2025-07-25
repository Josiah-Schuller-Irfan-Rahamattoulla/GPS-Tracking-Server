from psycopg2.extensions import connection as PGConnection
from psycopg2.extras import RealDictCursor
import hashlib
import secrets

from db.models import User


def hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    """
    Hash a password with a salt using PBKDF2.

    :param password: Plain text password to hash
    :param salt: Optional salt to use. If not provided, a new salt will be generated
    :return: Tuple of (hashed_password, salt)
    """
    if salt is None:
        salt = secrets.token_hex(16)

    hashed_password = hashlib.pbkdf2_hmac(
        "sha256", password.encode(), salt.encode(), 100000
    ).hex()
    return hashed_password, salt


def generate_access_token() -> str:
    """
    Generate a secure random access token.

    :return: Randomly generated access token
    """
    return secrets.token_urlsafe(32)


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


def get_user_by_email(db_conn: PGConnection, email_address: str) -> User | None:
    """
    Retrieve a user from the database by their email address.

    :param email_address: Email address of the user to retrieve
    :param db_conn: Database connection object
    :return: User data if found, None otherwise
    """
    with db_conn:
        with db_conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                "SELECT * FROM users WHERE email_address = %s", (email_address,)
            )
            row = cursor.fetchone()
            return User(**row) if row else None


def create_user(
    db_conn: PGConnection,
    email_address: str,
    phone_number: str,
    name: str,
    password: str,
) -> User:
    """
    Create a new user in the database.

    :param db_conn: Database connection object
    :param email_address: User's email address
    :param phone_number: User's phone number
    :param name: User's name
    :param password: User's plain text password (will be hashed)
    :return: Created user data
    """
    # Generate salt and hash password
    hashed_password, salt = hash_password(password=password)

    # Generate access token
    access_token = generate_access_token()

    with db_conn:
        with db_conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                """
                INSERT INTO users (email_address, phone_number, name, salt, hashed_password, access_token)
                VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING *
                """,
                (
                    email_address,
                    phone_number,
                    name,
                    salt,
                    hashed_password,
                    access_token,
                ),
            )
            row = cursor.fetchone()
            return User(**row)


def verify_user_password(
    db_conn: PGConnection, email_address: str, password: str
) -> User | None:
    """
    Verify a user's password and return the user if valid.

    :param db_conn: Database connection object
    :param email_address: User's email address
    :param password: User's plain text password
    :return: User data if password is valid, None otherwise
    """
    user = get_user_by_email(db_conn, email_address)
    if user is None:
        return None

    # Hash the provided password with the stored salt
    hashed_password, _ = hash_password(password=password, salt=user.salt)

    if hashed_password == user.hashed_password:
        return user
    return None
