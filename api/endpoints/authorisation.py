import os

from fastapi import HTTPException, Request, Query, Security, status
from fastapi.security import APIKeyHeader
from psycopg2 import connect

from api.db.devices import get_device
from api.db.users import get_user

access_token_header = APIKeyHeader(name="Access-Token", auto_error=False)


async def authorise_device(
    request: Request, access_token: str = Security(access_token_header)
):
    """
    Authorises a device based on its device_id and access token.
    For GET (e.g. /agnss) device_id comes from query; for POST from body.
    """
    if request.method == "GET":
        device_id = request.query_params.get("device_id")
    else:
        try:
            body = await request.json()
        except Exception:
            body = {}
        device_id = body.get("device_id") if isinstance(body, dict) else None

    if not device_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Device ID is required"
        )
    try:
        device_id = int(device_id)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Device ID must be an integer"
        )

    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Access token is required"
        )

    database_uri = os.getenv("DATABASE_URI")
    if not database_uri:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="DATABASE_URI not configured",
        )

    try:
        db_conn = connect(dsn=database_uri)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connection failed: {type(e).__name__}: {e}",
        )

    try:
        device = get_device(db_conn=db_conn, device_id=device_id)
    finally:
        try:
            db_conn.close()
        except Exception:
            pass
    if device is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Device ID does not exist"
        )

    if device.access_token != access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token"
        )


async def authorise_user(
    request: Request,
    access_token: str = Security(access_token_header),
    user_id: int = Query(None, description="User ID"),
):
    """
    Authorises a user based on their access token.
    """
    # Try getting user_id from the query parameters first
    if user_id is None:
        # If user_id is not provided in the query, try to get it from the request body
        try:
            body = await request.json()
            user_id = body.get("user_id")
        except Exception:
            # Body might not be JSON or might be empty (e.g., GET requests)
            pass

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="User ID is required"
        )

    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Access token is required"
        )

    database_uri = os.getenv("DATABASE_URI")
    if not database_uri:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="DATABASE_URI not configured",
        )

    try:
        db_conn = connect(dsn=database_uri)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connection failed: {type(e).__name__}: {e}",
        )

    try:
        user = get_user(db_conn=db_conn, user_id=user_id)
    finally:
        try:
            db_conn.close()
        except Exception:
            pass
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User ID does not exist"
        )

    if user.access_token != access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token"
        )
