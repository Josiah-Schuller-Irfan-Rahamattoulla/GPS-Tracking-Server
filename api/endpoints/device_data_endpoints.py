import logging
import os
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, Security, status

logger = logging.getLogger(__name__)
from fastapi.security import APIKeyHeader
from fastapi.responses import Response
from psycopg2 import connect
from psycopg2 import IntegrityError, OperationalError
from pydantic import BaseModel
import httpx

from db.devices import create_device, get_device, get_user_ids_for_device
from db.gps_data import add_gps_data
from db.geofences import get_geofences_by_user_id
from db.geofence_breaches import check_geofence_breaches
from db.models import GeofenceBreachEvent
from db.users import get_user
from notifications.geofence_breach_notifications import notify_geofence_breach_events
from notifications.sms_notifications import notify_geofence_breach_via_sms

access_token_header = APIKeyHeader(name="Access-Token", auto_error=False)

router = APIRouter()

device_registration_router = APIRouter()  # Router for device registration endpoints


class DeviceData(BaseModel):
    device_id: int
    latitude: float
    longitude: float
    timestamp: datetime
    speed: float | None = None
    heading: float | None = None
    trip_active: bool | None = None
    
    @classmethod
    def __get_validators__(cls):
        yield cls.validate_ranges
    
    @staticmethod
    def validate_ranges(v):
        if isinstance(v, dict):
            speed = v.get('speed')
            heading = v.get('heading')
            
            if speed is not None and speed < 0:
                raise ValueError('speed must be >= 0')
            if heading is not None and not (0 <= heading <= 360):
                raise ValueError('heading must be between 0 and 360')
        return v

    @classmethod
    def __get_validators__(cls):
        yield from super().__get_validators__()
        yield cls.validate_heading

    @staticmethod
    def validate_heading(values):
        heading = values.get('heading')
        if heading is not None:
            if not (0 <= heading <= 360):
                raise ValueError("heading must be between 0 and 360 degrees")
        return values
class DeviceDataResponse(BaseModel):
    success: bool
    message: str


@router.post("/sendGPSData", response_model=DeviceDataResponse)
async def send_gps_data(device_data: DeviceData):
    """
    Endpoint to receive GPS data from a device.
    Supports speed, heading, and trip_active fields from hardware/mobile app.
    If device timestamp is stale (before 2020), use server time so web UI finds it.
    
    Now includes server-side geofence breach detection for all users with access to the device.
    """
    db_conn = connect(dsn=os.getenv("DATABASE_URI"))

    ts = device_data.timestamp
    if ts.year < 2020:
        ts = datetime.now(timezone.utc)

    # Store GPS data
    add_gps_data(
        db_conn=db_conn,
        device_id=device_data.device_id,
        timestamp=ts,
        latitude=device_data.latitude,
        longitude=device_data.longitude,
        speed=device_data.speed,
        heading=device_data.heading,
        trip_active=device_data.trip_active,
    )

    # Check geofence breaches for all users who have access to this device
    user_ids = get_user_ids_for_device(db_conn, device_data.device_id)
    all_breach_events: list[GeofenceBreachEvent] = []
    
    for user_id in user_ids:
        # Get all active geofences for this user
        geofences = get_geofences_by_user_id(db_conn, user_id)
        
        # Check for breaches
        breach_events = check_geofence_breaches(
            db_conn=db_conn,
            device_id=device_data.device_id,
            user_id=user_id,
            latitude=device_data.latitude,
            longitude=device_data.longitude,
            geofences=geofences
        )
        
        if breach_events:
            # Send notifications for this user
            user = get_user(db_conn, user_id)
            device = get_device(db_conn, device_data.device_id)
            geofences_by_id = {g.geofence_id: g for g in geofences}
            
            # Send email notifications
            notify_geofence_breach_events(
                db_conn=db_conn,
                events=breach_events,
                user=user,
                device=device,
                geofences_by_id=geofences_by_id
            )
            
            # Send SMS notifications
            notify_geofence_breach_via_sms(
                db_conn=db_conn,
                events=breach_events,
                user=user,
                device=device,
                geofences_by_id=geofences_by_id
            )
        
        all_breach_events.extend(breach_events)
    
    # Log breach summary if any occurred
    if all_breach_events:
        logger.info(
            f"GPS data triggered {len(all_breach_events)} geofence breach(es) "
            f"for device {device_data.device_id}"
        )

    return DeviceDataResponse(
        success=True,
        message="GPS data saved successfully",
    )


class DeviceRegistrationData(BaseModel):
    device_id: int
    access_token: str
    sms_number: str
    name: str | None = None
    control_1: bool | None = None
    control_2: bool | None = None
    control_3: bool | None = None
    control_4: bool | None = None


@device_registration_router.post("/registerDevice")
async def register_device(device_data: DeviceRegistrationData):
    """
    Endpoint to register a new device.
    """
    database_uri = os.getenv("DATABASE_URI")
    if not database_uri:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="DATABASE_URI not configured",
        )
    try:
        db_conn = connect(dsn=database_uri)
    except OperationalError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database unavailable: {str(e)}",
        )

    # Check if device already exists
    existing_device = get_device(
        db_conn=db_conn, device_id=device_data.device_id
    )
    if existing_device:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Device with this ID already exists",
        )

    try:
        create_device(
            db_conn=db_conn,
            device_id=device_data.device_id,
            access_token=device_data.access_token,
            sms_number=device_data.sms_number,
            name=device_data.name,
            control_1=device_data.control_1,
            control_2=device_data.control_2,
            control_3=device_data.control_3,
            control_4=device_data.control_4,
        )
    except IntegrityError as e:
        db_conn.rollback()
        if "device_id" in str(e):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Device with this ID already exists",
            )
        if "sms_number" in str(e):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="SMS number already registered to another device",
            )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Device or SMS number already exists",
        )

    return {"success": True, "message": "Device registered successfully"}


@router.get("/getDeviceControls")
async def get_device_controls(
    device_id: int = Query(..., description="Device ID"),
    access_token: str = Security(access_token_header)
):
    """
    Endpoint for devices to get their control settings.
    Authenticated using device access token in header.
    """
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token is required"
        )
    
    db_conn = connect(dsn=os.getenv("DATABASE_URI"))
    
    # Verify device and token
    device = get_device(db_conn=db_conn, device_id=device_id)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    
    if device.access_token != access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token"
        )
    
    return {
        "device_id": device.device_id,
        "control_1": device.control_1,
        "control_2": device.control_2,
        "control_3": device.control_3,
        "control_4": device.control_4,
        "control_version": device.control_version,
        "controls_updated_at": device.controls_updated_at.isoformat() if device.controls_updated_at else None
    }


@router.get("/agnss")
async def get_agnss_data(
    device_id: int = Query(..., description="Device ID"),
    lat: float | None = Query(None, ge=-90, le=90, description="Approximate latitude for tailored A-GNSS"),
    lon: float | None = Query(None, ge=-180, le=180, description="Approximate longitude for tailored A-GNSS"),
    access_token: str = Security(access_token_header)
):
    """
    A-GNSS proxy endpoint: fetches assistance data from nRF Cloud and returns the binary blob
    byte-for-byte unchanged. The device expects the exact nRF Cloud A-GPS format; no decoding,
    stripping, or transcoding is applied. Optional lat/lon request location-tailored data for faster TTFF.
    """
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token is required"
        )
    
    db_conn = connect(dsn=os.getenv("DATABASE_URI"))
    
    # Verify device and token
    device = get_device(db_conn=db_conn, device_id=device_id)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    
    if device.access_token != access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token"
        )
    
    # Fetch A-GNSS data from nRF Cloud (Bearer token = JWT from nRF Cloud; typically valid ~30 days)
    nrf_cloud_api_key = os.getenv("NRF_CLOUD_API_KEY")
    if not nrf_cloud_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="nRF Cloud API key not configured"
        )
    
    # Use device_id as deviceIdentifier (or could use IMEI if stored)
    # nRF Cloud accepts various identifiers; device_id should work for caching
    device_identifier = f"nrf-{device_id}"
    url = "https://api.nrfcloud.com/v1/location/agps"
    auth_headers = {"Authorization": f"Bearer {nrf_cloud_api_key}"}
    params: dict[str, str | float] = {"deviceIdentifier": device_identifier}
    if lat is not None and lon is not None:
        params["latitude"] = lat
        params["longitude"] = lon
        logger.info("A-GNSS request with position hint: lat=%.6f lon=%.6f", lat, lon)

    def _parse_content_range(header_value: str | None) -> int | None:
        """Parse Content-Range (e.g. 'bytes 0-396/12345') and return total size, or None."""
        if not header_value:
            return None
        try:
            # "bytes start-end/total" or "bytes start-end/*"
            parts = header_value.strip().split()
            if len(parts) != 2 or parts[0].lower() != "bytes":
                return None
            range_part = parts[1]
            if "/" not in range_part:
                return None
            _, total_part = range_part.split("/", 1)
            if total_part == "*":
                return None
            return int(total_part)
        except (ValueError, IndexError):
            return None

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # nRF Cloud A-GPS requires a Range header (422 otherwise). Request up to 16KB first.
            response = await client.get(
                url,
                params=params,
                headers={**auth_headers, "Range": "bytes=0-16383"},
            )

            if response.status_code not in (200, 206):
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"nRF Cloud returned status {response.status_code}: {response.text}",
                )

            content_range = response.headers.get("Content-Range")
            body_len = len(response.content)
            logger.info(
                "nRF Cloud A-GPS: status=%s Content-Range=%s body_len=%s",
                response.status_code,
                content_range,
                body_len,
            )

            chunks = [response.content]
            total_received = body_len
            total_size = _parse_content_range(content_range)

            # If 206 and Content-Range indicates more data, fetch remaining ranges.
            while total_size is not None and total_received < total_size:
                next_start = total_received
                range_header = f"bytes={next_start}-"
                next_response = await client.get(
                    url,
                    params=params,
                    headers={**auth_headers, "Range": range_header},
                )
                if next_response.status_code not in (200, 206):
                    break
                chunk = next_response.content
                if not chunk:
                    break
                chunks.append(chunk)
                total_received += len(chunk)

            # If we got 206 but no total (e.g. "bytes 0-396/*"), try fetching next range until empty.
            if total_size is None and response.status_code == 206 and body_len > 0:
                next_start = total_received
                while True:
                    next_response = await client.get(
                        url,
                        params=params,
                        headers={**auth_headers, "Range": f"bytes={next_start}-"},
                    )
                    if next_response.status_code not in (200, 206):
                        break
                    chunk = next_response.content
                    if not chunk:
                        break
                    chunks.append(chunk)
                    total_received += len(chunk)
                    next_start = total_received
                    if len(chunk) < 4096:  # assume last chunk if smaller than 4K
                        break

            # Return nRF Cloud body byte-for-byte (no decode/transcode) so modem A-GNSS inject works
            full_content = b"".join(chunks)
            logger.info("A-GNSS proxy returning %s bytes to device (raw binary)", len(full_content))

            return Response(
                content=full_content,
                media_type="application/octet-stream",
                headers={"Content-Length": str(len(full_content))},
            )

    except httpx.RequestError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch A-GNSS from nRF Cloud: {str(e)}",
        )
