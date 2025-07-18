from fastapi import HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader

from db.database import PGDatabase
from db.devices import get_device

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
