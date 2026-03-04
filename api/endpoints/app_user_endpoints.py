import hmac
import os
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Query, status
from psycopg2 import connect
from pydantic import BaseModel

from api.db.devices import get_devices_by_user_id, get_device_by_user, update_device_controls, update_device_tracking, delete_all_devices, create_user_device_row, get_device
from api.db.gps_data import get_gps_data
from api.db.models import GPSData
from api.db.users import get_user, get_user_by_email, create_user, verify_user_password
from api.db.geofences import (
    get_geofences_by_user_id,
    create_geofence,
    update_geofence,
    delete_geofence,
)
from api.db.models import GeofenceBreachEvent
from psycopg2.extras import RealDictCursor
from api.endpoints.realtime_endpoints import broadcast_device_control_response

router = APIRouter()  # Router for authenticated endpoints
auth_router = APIRouter()  # Router for unauthenticated endpoints (login/signup)


# Pydantic models for login/signup
class SignupRequest(BaseModel):
    email_address: str
    phone_number: str
    name: str
    password: str


class LoginRequest(BaseModel):
    email_address: str
    password: str


class AuthResponse(BaseModel):
    user_id: int
    email_address: str
    phone_number: str
    name: str
    access_token: str


# Authentication endpoints (no authorization required)
@auth_router.post("/signup", response_model=AuthResponse)
async def signup(request: SignupRequest):
    """
    Endpoint to create a new user account.
    """
    db_conn = connect(dsn=os.getenv("DATABASE_URI"))

    # Check if user already exists
    existing_user = get_user_by_email(
        db_conn=db_conn, email_address=request.email_address
    )
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email address already exists",
        )

    # Create new user
    try:
        new_user = create_user(
            db_conn=db_conn,
            email_address=request.email_address,
            phone_number=request.phone_number,
            name=request.name,
            password=request.password,
        )

        return AuthResponse(
            user_id=new_user.user_id,
            email_address=new_user.email_address,
            phone_number=new_user.phone_number,
            name=new_user.name,
            access_token=new_user.access_token,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user: {str(e)}",
        )


@auth_router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest):
    """
    Endpoint to authenticate a user and return their access token.
    """
    db_conn = connect(dsn=os.getenv("DATABASE_URI"))

    # Verify user credentials
    user = verify_user_password(
        db_conn=db_conn,
        email_address=request.email_address,
        password=request.password,
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email address or password",
        )

    return AuthResponse(
        user_id=user.user_id,
        email_address=user.email_address,
        phone_number=user.phone_number,
        name=user.name,
        access_token=user.access_token,
    )


class AppUserResponse(BaseModel):
    user_id: int
    email_address: str
    phone_number: str
    name: str


@router.get("/user", response_model=AppUserResponse)
async def get_user_info(
    user_id: int = Query(..., description="User ID"),
):
    """
    Endpoint to retrieve user information.
    """
    db_conn = connect(dsn=os.getenv("DATABASE_URI"))
    user = get_user(db_conn=db_conn, user_id=user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    return AppUserResponse(
        user_id=user.user_id,
        email_address=user.email_address,
        phone_number=user.phone_number,
        name=user.name,
    )


class AppDeviceResponse(BaseModel):
    device_id: int
    sms_number: str
    name: str | None = None
    remote_viewing: bool | None = None
    last_viewed_at: datetime | None = None
    control_1: bool | None
    control_2: bool | None
    control_3: bool | None
    control_4: bool | None
    control_version: int | None = None
    controls_updated_at: datetime | None = None


class LinkDeviceRequest(BaseModel):
    device_id: int
    access_token: str  # Device pairing code (printed on sticker); required to prove ownership


@router.post("/registerDeviceToUser")
async def register_device_to_user(
    request: LinkDeviceRequest,
    user_id: int = Query(..., description="User ID"),
):
    """
    Link an existing device to a user. Requires user auth and the device's access_token
    (pairing code) so only someone with the sticker/device can claim it.
    """
    db_conn = connect(dsn=os.getenv("DATABASE_URI"))
    device = get_device(db_conn=db_conn, device_id=request.device_id)
    if device is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        )
    if not request.access_token or not hmac.compare_digest(device.access_token, request.access_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid pairing code for this device",
        )
    create_user_device_row(
        db_conn=db_conn,
        user_id=user_id,
        device_id=request.device_id,
    )
    return {"success": True, "message": "Device registered to user successfully"}


@router.get("/devices", response_model=list[AppDeviceResponse])
async def get_user_devices(
    user_id: int = Query(..., description="User ID"),
):
    """
    Endpoint to retrieve devices associated with a user.
    """
    db_conn = connect(dsn=os.getenv("DATABASE_URI"))

    devices = get_devices_by_user_id(db_conn=db_conn, user_id=user_id)

    return [
        AppDeviceResponse(
            device_id=device.device_id,
            sms_number=device.sms_number,
            name=device.name,
            remote_viewing=device.remote_viewing,
            last_viewed_at=device.last_viewed_at,
            control_1=device.control_1,
            control_2=device.control_2,
            control_3=device.control_3,
            control_4=device.control_4,
            control_version=device.control_version,
            controls_updated_at=device.controls_updated_at,
        )
        for device in devices
    ]


class AppGPSDataResponse(BaseModel):
    gps_data: list[GPSData]


@router.get("/GPSData", response_model=AppGPSDataResponse)
async def get_device_gps_data(
    user_id: int = Query(..., description="User ID"),  # Required for authorisation
    device_id: int = Query(..., description="Device ID"),
    start_time: datetime = Query(
        ..., description="Start time of the GPS data to fetch"
    ),
    end_time: datetime = Query(..., description="End time of the GPS data to fetch"),
):
    """
    Endpoint to receive GPS data from a device.
    """
    if end_time <= start_time:
        raise ValueError("end_time must be greater than start_time")

    db_conn = connect(dsn=os.getenv("DATABASE_URI"))
    
    # Verify user owns device
    device = get_device_by_user(db_conn=db_conn, device_id=device_id, user_id=user_id)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found or not owned by user",
        )

    gps_data = get_gps_data(
        db_conn=db_conn,
        device_id=device_id,
        start_time=start_time,
        end_time=end_time,
    )

    return AppGPSDataResponse(
        gps_data=gps_data,
    )


from fastapi import Header

@router.get("/devices/{device_id}", response_model=AppDeviceResponse)
async def get_device_endpoint(
    device_id: int,
    user_id: int | None = Query(None, description="User ID"),
    access_token: str = Header(None, alias="Access-Token")
):
    """
    Get a single device by ID. Allows access by user ownership or valid device access token.
    """
    db_conn = connect(dsn=os.getenv("DATABASE_URI"))
    # Device access: allow with valid device access token, no user_id required
    device = None
    if access_token:
        dev = get_device(db_conn=db_conn, device_id=device_id)
        if dev:
            if dev.access_token == access_token:
                device = dev
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid access token",
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Device not found",
            )
    elif user_id is not None:
        device = get_device_by_user(db_conn=db_conn, device_id=device_id, user_id=user_id)
        if not device:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Device not found for user",
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token is required",
        )
    return AppDeviceResponse(
        device_id=device.device_id,
        sms_number=device.sms_number,
        name=device.name,
        remote_viewing=device.remote_viewing,
        last_viewed_at=device.last_viewed_at,
        control_1=device.control_1,
        control_2=device.control_2,
        control_3=device.control_3,
        control_4=device.control_4,
        control_version=device.control_version,
        controls_updated_at=device.controls_updated_at,
    )


class DeviceTrackingUpdate(BaseModel):
    remote_viewing: bool | None = None  # Set true when web/app is actively viewing device


@router.put("/devices/{device_id}/tracking", response_model=AppDeviceResponse)
async def update_device_tracking_endpoint(
    device_id: int,
    tracking: DeviceTrackingUpdate,
    user_id: int = Query(..., description="User ID"),
):
    """
    Update device tracking configuration (hot/cold mode and upload intervals).
    """
    db_conn = connect(dsn=os.getenv("DATABASE_URI"))

    updated_device = update_device_tracking(
        db_conn=db_conn,
        device_id=device_id,
        user_id=user_id,
        remote_viewing=tracking.remote_viewing,
    )

    if not updated_device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found or not owned by user",
        )

    return AppDeviceResponse(
        device_id=updated_device.device_id,
        sms_number=updated_device.sms_number,
        name=updated_device.name,
        remote_viewing=updated_device.remote_viewing,
        last_viewed_at=updated_device.last_viewed_at,
        control_1=updated_device.control_1,
        control_2=updated_device.control_2,
        control_3=updated_device.control_3,
        control_4=updated_device.control_4,
        control_version=updated_device.control_version,
        controls_updated_at=updated_device.controls_updated_at,
    )


class DeviceControlsUpdate(BaseModel):
    control_1: bool | None = None
    control_2: bool | None = None
    control_3: bool | None = None
    control_4: bool | None = None
    expected_version: int | None = None  # For optimistic locking


@router.put("/devices/{device_id}/controls", response_model=AppDeviceResponse)
async def update_device_controls_endpoint(
    device_id: int,
    controls: DeviceControlsUpdate,
    user_id: int = Query(..., description="User ID"),
):
    """
    Update device control flags (kill switch, etc.).
    Supports optimistic locking via expected_version.
    """
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
        updated_device = update_device_controls(
            db_conn=db_conn,
            device_id=device_id,
            user_id=user_id,
            control_1=controls.control_1,
            control_2=controls.control_2,
            control_3=controls.control_3,
            control_4=controls.control_4,
            expected_version=controls.expected_version,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"update_device_controls failed: {type(e).__name__}: {e}",
        )
    
    if not updated_device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found, not owned by user, or version conflict",
        )

    await broadcast_device_control_response(device_id, {
        "device_id": updated_device.device_id,
        "control_1": updated_device.control_1,
        "control_2": updated_device.control_2,
        "control_3": updated_device.control_3,
        "control_4": updated_device.control_4,
        "control_version": updated_device.control_version,
        "controls_updated_at": updated_device.controls_updated_at.isoformat() if updated_device.controls_updated_at else None,
    })
    
    return AppDeviceResponse(
        device_id=updated_device.device_id,
        sms_number=updated_device.sms_number,
        name=updated_device.name,
        control_1=updated_device.control_1,
        control_2=updated_device.control_2,
        control_3=updated_device.control_3,
        control_4=updated_device.control_4,
        control_version=updated_device.control_version,
        controls_updated_at=updated_device.controls_updated_at,
    )


class TripStatusResponse(BaseModel):
    trip_active: bool
    last_trip_time: datetime | None = None
    last_gps_time: datetime | None = None


@router.get("/devices/{device_id}/trip", response_model=TripStatusResponse)
async def get_device_trip_status(
    device_id: int,
    user_id: int = Query(..., description="User ID"),
):
    """
    Get current trip status from hardware IMU detection.
    Returns the latest trip_active flag from GPS data.
    """
    db_conn = connect(dsn=os.getenv("DATABASE_URI"))
    
    # Verify user owns device
    device = get_device_by_user(db_conn=db_conn, device_id=device_id, user_id=user_id)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found or not owned by user",
        )
    
    # Get latest GPS data with trip_active
    from datetime import timezone
    end_time = datetime.now(timezone.utc).replace(tzinfo=None)
    start_time = end_time - timedelta(hours=1)  # Last hour
    
    gps_records = get_gps_data(
        db_conn=db_conn,
        device_id=device_id,
        start_time=start_time,
        end_time=end_time,
    )
    
    # Find latest record with trip_active
    trip_active = False
    last_trip_time = None
    last_gps_time = None
    
    if gps_records:
        # Sort by time descending
        gps_records.sort(key=lambda x: x.time, reverse=True)
        latest = gps_records[0]
        last_gps_time = latest.time
        trip_active = latest.trip_active if latest.trip_active is not None else False
        
        # Find last time trip was active
        for record in gps_records:
            if record.trip_active:
                last_trip_time = record.time
                break
    
    return TripStatusResponse(
        trip_active=trip_active,
        last_trip_time=last_trip_time,
        last_gps_time=last_gps_time,
    )


# ============== Geofence Endpoints ==============

class GeofenceResponse(BaseModel):
    geofence_id: int
    user_id: int
    name: str
    latitude: float
    longitude: float
    radius: float
    enabled: bool
    created_at: datetime


class GeofenceCreate(BaseModel):
    name: str
    latitude: float
    longitude: float
    radius: float = 100.0
    enabled: bool = True
    
    @classmethod
    def __get_validators__(cls):
        yield cls.validate_coordinates
    
    @staticmethod
    def validate_coordinates(v):
        if isinstance(v, dict):
            lat = v.get('latitude')
            lon = v.get('longitude')
            rad = v.get('radius', 100.0)
            
            if lat is not None and not (-90 <= lat <= 90):
                raise ValueError('latitude must be between -90 and 90')
            if lon is not None and not (-180 <= lon <= 180):
                raise ValueError('longitude must be between -180 and 180')
            if rad is not None and rad <= 0:
                raise ValueError('radius must be greater than 0')
        return v


class GeofenceUpdate(BaseModel):
    name: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    radius: float | None = None
    enabled: bool | None = None


@router.get("/geofences", response_model=list[GeofenceResponse])
async def get_geofences(
    user_id: int = Query(..., description="User ID"),
):
    """
    Get all geofences for a user.
    """
    db_conn = connect(dsn=os.getenv("DATABASE_URI"))
    
    geofences = get_geofences_by_user_id(db_conn=db_conn, user_id=user_id)
    
    return [
        GeofenceResponse(
            geofence_id=g.geofence_id,
            user_id=g.user_id,
            name=g.name,
            latitude=g.latitude,
            longitude=g.longitude,
            radius=g.radius,
            enabled=g.enabled,
            created_at=g.created_at,
        )
        for g in geofences
    ]


@router.post("/geofences", response_model=GeofenceResponse)
async def create_geofence_endpoint(
    geofence: GeofenceCreate,
    user_id: int = Query(..., description="User ID"),
):
    """
    Create a new geofence for a user.
    """
    db_conn = connect(dsn=os.getenv("DATABASE_URI"))
    
    new_geofence = create_geofence(
        db_conn=db_conn,
        user_id=user_id,
        name=geofence.name,
        latitude=geofence.latitude,
        longitude=geofence.longitude,
        radius=geofence.radius,
        enabled=geofence.enabled,
    )
    
    return GeofenceResponse(
        geofence_id=new_geofence.geofence_id,
        user_id=new_geofence.user_id,
        name=new_geofence.name,
        latitude=new_geofence.latitude,
        longitude=new_geofence.longitude,
        radius=new_geofence.radius,
        enabled=new_geofence.enabled,
        created_at=new_geofence.created_at,
    )


@router.put("/geofences/{geofence_id}", response_model=GeofenceResponse)
async def update_geofence_endpoint(
    geofence_id: int,
    geofence: GeofenceUpdate,
    user_id: int = Query(..., description="User ID"),
):
    """
    Update an existing geofence.
    """
    db_conn = connect(dsn=os.getenv("DATABASE_URI"))
    
    updated = update_geofence(
        db_conn=db_conn,
        geofence_id=geofence_id,
        user_id=user_id,
        name=geofence.name,
        latitude=geofence.latitude,
        longitude=geofence.longitude,
        radius=geofence.radius,
        enabled=geofence.enabled,
    )
    
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Geofence not found or not owned by user",
        )
    
    return GeofenceResponse(
        geofence_id=updated.geofence_id,
        user_id=updated.user_id,
        name=updated.name,
        latitude=updated.latitude,
        longitude=updated.longitude,
        radius=updated.radius,
        enabled=updated.enabled,
        created_at=updated.created_at,
    )


@router.delete("/geofences/{geofence_id}")
async def delete_geofence_endpoint(
    geofence_id: int,
    user_id: int = Query(..., description="User ID"),
):
    """
    Delete a geofence.
    """
    db_conn = connect(dsn=os.getenv("DATABASE_URI"))
    
    deleted = delete_geofence(
        db_conn=db_conn,
        geofence_id=geofence_id,
        user_id=user_id,
    )
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Geofence not found or not owned by user",
        )
    
    return {"success": True, "message": "Geofence deleted successfully"}


# ============== Geofence Breach Events Endpoints ==============

class GeofenceBreachEventResponse(BaseModel):
    event_id: int
    device_id: int
    geofence_id: int
    geofence_name: str
    device_name: str | None
    event_type: str  # 'ENTERED' or 'EXITED'
    latitude: float
    longitude: float
    event_time: datetime
    notification_sent: bool


@router.get("/geofence-breach-events", response_model=list[GeofenceBreachEventResponse])
async def get_geofence_breach_events(
    user_id: int = Query(..., description="User ID"),
    device_id: int | None = Query(None, description="Filter by device ID"),
    geofence_id: int | None = Query(None, description="Filter by geofence ID"),
    event_type: str | None = Query(None, description="Filter by event type (ENTERED/EXITED)"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of events to return"),
):
    """
    Get geofence breach events for the user's devices.
    Returns events with device and geofence names for easy display.
    """
    db_conn = connect(dsn=os.getenv("DATABASE_URI"))
    
    # Build query with optional filters
    query = """
        SELECT 
            gbe.event_id,
            gbe.device_id,
            gbe.geofence_id,
            gf.name as geofence_name,
            d.name as device_name,
            gbe.event_type,
            gbe.latitude,
            gbe.longitude,
            gbe.event_time,
            gbe.notification_sent
        FROM geofence_breach_events gbe
        JOIN geofences gf ON gbe.geofence_id = gf.geofence_id
        JOIN devices d ON gbe.device_id = d.device_id
        WHERE gbe.user_id = %s
    """
    params = [user_id]
    
    if device_id is not None:
        query += " AND gbe.device_id = %s"
        params.append(device_id)
    
    if geofence_id is not None:
        query += " AND gbe.geofence_id = %s"
        params.append(geofence_id)
    
    if event_type is not None:
        query += " AND gbe.event_type = %s"
        params.append(event_type.upper())
    
    query += " ORDER BY gbe.event_time DESC LIMIT %s"
    params.append(limit)
    
    with db_conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(query, params)
        events = cursor.fetchall()
        return [GeofenceBreachEventResponse(**event) for event in events]


# ============== Device Management Endpoints ==============

class DeleteAllDevicesResponse(BaseModel):
    success: bool
    message: str
    devices_deleted: int


@router.delete("/devices/all", response_model=DeleteAllDevicesResponse)
async def delete_all_user_devices(
    user_id: int = Query(..., description="User ID for authorization"),
):
    """
    Delete all devices associated with a user.
    This will delete:
    - All GPS data for those devices
    - All geofences for this user
    - All user-device links
    - The devices themselves
    
    WARNING: This action cannot be undone!
    """
    db_conn = connect(dsn=os.getenv("DATABASE_URI"))
    
    try:
        devices_deleted = delete_all_devices(db_conn=db_conn, user_id=user_id)
        
        return DeleteAllDevicesResponse(
            success=True,
            message=f"Successfully deleted {devices_deleted} device(s) and all associated data",
            devices_deleted=devices_deleted,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete devices: {str(e)}",
        )


@router.get("/geofence-breach-events")
async def get_geofence_breach_events(
    user_id: int = Query(..., description="User ID"),
    geofence_id: int = Query(None, description="Filter by geofence ID (optional)"),
    device_id: int = Query(None, description="Filter by device ID (optional)"),
    event_type: str = Query(None, description="Filter by event type: ENTERED or EXITED (optional)"),
    limit: int = Query(50, description="Maximum number of events to return"),
    offset: int = Query(0, description="Number of events to skip"),
):
    """
    Endpoint to retrieve geofence breach events for a user.
    Can filter by geofence_id, device_id, and event_type.
    """
    db_conn = connect(dsn=os.getenv("DATABASE_URI"))
    
    query = "SELECT * FROM geofence_breach_events WHERE user_id = %s"
    params = [user_id]
    
    if geofence_id is not None:
        query += " AND geofence_id = %s"
        params.append(geofence_id)
    
    if device_id is not None:
        query += " AND device_id = %s"
        params.append(device_id)
    
    if event_type is not None:
        if event_type not in ['ENTERED', 'EXITED']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="event_type must be 'ENTERED' or 'EXITED'",
            )
        query += " AND event_type = %s"
        params.append(event_type)
    
    query += " ORDER BY event_time DESC LIMIT %s OFFSET %s"
    params.extend([limit, offset])
    
    try:
        with db_conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query, params)
            events = cursor.fetchall()
        
        # Convert to response format (rename id field if needed)
        return [
            {
                "geofence_breach_event_id": event['event_id'],
                "device_id": event['device_id'],
                "geofence_id": event['geofence_id'],
                "event_type": event['event_type'],
                "latitude": event['latitude'],
                "longitude": event['longitude'],
                "event_time": event['event_time'],
                "notification_sent": event['notification_sent'],
                "notification_method": event['notification_method'],
            }
            for event in events
        ]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve breach events: {str(e)}",
        )
