from fastapi import HTTPException, Request, Query, Security, status
from fastapi.security import APIKeyHeader

from db.database import PGDatabase
from db.devices import get_device
from db.users import get_user

access_token_header = APIKeyHeader(name="Access-Token", auto_error=False)


async def authorise_device(
    request: Request, access_token: str = Security(access_token_header)
):
    """
    Authorises a device based on its device_id and access token.
    """
    body = await request.json()
    device_id = body.get("device_id")

    if not device_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Device ID is required"
        )

    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Access token is required"
        )

    db_conn = PGDatabase.connect_to_db()
    device = get_device(db_conn=db_conn.connection, device_id=device_id)
    if device is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Device ID does not exist"
        )

    if device.access_token != access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token"
        )


async def authorise_user(
    request: Request, access_token: str = Security(access_token_header),
    user_id: int = Query(None, description="User ID")
):
    """
    Authorises a user based on their access token.
    """
    # Try getting user_id from the query parameters first
    if user_id is None:
        # If user_id is not provided in the query, try to get it from the request body
        body = await request.json()
        user_id = body.get("user_id")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="User ID is required"
        )

    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Access token is required"
        )

    db_conn = PGDatabase.connect_to_db()
    user = get_user(db_conn=db_conn.connection, user_id=user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User ID does not exist"
        )

    if user.access_token != access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token"
        )
