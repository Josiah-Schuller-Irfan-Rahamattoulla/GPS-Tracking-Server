import os
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Query, status
from psycopg2 import connect
from pydantic import BaseModel

from db.devices import get_devices_by_user_id, get_device_by_user, update_device_controls, get_device, delete_all_devices
from db.gps_data import get_gps_data
from db.models import GPSData
from db.users import get_user, get_user_by_email, create_user, verify_user_password
from db.geofences import (
    get_geofences_by_user_id,
    get_geofence,
    create_geofence,
    update_geofence,
    delete_geofence,
)

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
    control_1: bool | None
    control_2: bool | None
    control_3: bool | None
    control_4: bool | None
    control_version: int | None = None
    controls_updated_at: datetime | None = None


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


@router.get("/devices/{device_id}", response_model=AppDeviceResponse)
async def get_device_endpoint(
    device_id: int,
    user_id: int = Query(..., description="User ID"),
):
    """
    Get a single device by ID. Verifies user owns the device.
    """
    db_conn = connect(dsn=os.getenv("DATABASE_URI"))
    
    device = get_device_by_user(db_conn=db_conn, device_id=device_id, user_id=user_id)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found or not owned by user",
        )
    
    return AppDeviceResponse(
        device_id=device.device_id,
        sms_number=device.sms_number,
        name=device.name,
        control_1=device.control_1,
        control_2=device.control_2,
        control_3=device.control_3,
        control_4=device.control_4,
        control_version=device.control_version,
        controls_updated_at=device.controls_updated_at,
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
    db_conn = connect(dsn=os.getenv("DATABASE_URI"))
    
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
    
    if not updated_device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found, not owned by user, or version conflict",
        )
    
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
    end_time = datetime.utcnow()
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
    - All geofences for those devices
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
