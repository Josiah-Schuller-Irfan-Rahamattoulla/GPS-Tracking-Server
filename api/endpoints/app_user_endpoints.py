import os
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, status
from psycopg2 import connect
from pydantic import BaseModel

from db.devices import get_devices_by_user_id, update_device_controls, get_device, delete_all_devices
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
    control_1: bool | None
    control_2: bool | None
    control_3: bool | None
    control_4: bool | None


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
            control_1=device.control_1,
            control_2=device.control_2,
            control_3=device.control_3,
            control_4=device.control_4,
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

    gps_data = get_gps_data(
        db_conn=db_conn,
        device_id=device_id,
        start_time=start_time,
        end_time=end_time,
    )

    return AppGPSDataResponse(
        gps_data=gps_data,
    )


class UpdateDeviceControlsRequest(BaseModel):
    control_1: bool | None = None
    control_2: bool | None = None
    control_3: bool | None = None
    control_4: bool | None = None


@router.put("/devices/{device_id}/controls", response_model=AppDeviceResponse)
async def update_device_controls_endpoint(
    device_id: int,
    request: UpdateDeviceControlsRequest,
    user_id: int = Query(..., description="User ID for authorization"),
):
    """
    Update control flags for a device (kill switch, current draw, etc.).
    All 4 control flags are set together.
    """
    db_conn = connect(dsn=os.getenv("DATABASE_URI"))

    # Verify the device belongs to the user
    user_devices = get_devices_by_user_id(db_conn=db_conn, user_id=user_id)
    device_ids = [d.device_id for d in user_devices]
    
    if device_id not in device_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Device does not belong to this user",
        )

    # Update the device controls
    updated_device = update_device_controls(
        db_conn=db_conn,
        device_id=device_id,
        control_1=request.control_1,
        control_2=request.control_2,
        control_3=request.control_3,
        control_4=request.control_4,
    )

    if updated_device is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        )

    return AppDeviceResponse(
        device_id=updated_device.device_id,
        sms_number=updated_device.sms_number,
        control_1=updated_device.control_1,
        control_2=updated_device.control_2,
        control_3=updated_device.control_3,
        control_4=updated_device.control_4,
    )


@router.get("/devices/{device_id}", response_model=AppDeviceResponse)
async def get_device_by_id(
    device_id: int,
    user_id: int = Query(..., description="User ID for authorization"),
):
    """
    Get a single device by ID.
    """
    db_conn = connect(dsn=os.getenv("DATABASE_URI"))

    # Verify the device belongs to the user
    user_devices = get_devices_by_user_id(db_conn=db_conn, user_id=user_id)
    device_ids = [d.device_id for d in user_devices]
    
    if device_id not in device_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Device does not belong to this user",
        )

    device = get_device(db_conn=db_conn, device_id=device_id)

    if device is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found",
        )

    return AppDeviceResponse(
        device_id=device.device_id,
        sms_number=device.sms_number,
        control_1=device.control_1,
        control_2=device.control_2,
        control_3=device.control_3,
        control_4=device.control_4,
    )


# ============== Geofence Endpoints ==============

class GeofenceResponse(BaseModel):
    geofence_id: int
    user_id: int
    name: str
    latitude: float
    longitude: float
    radius: int
    enabled: bool


class CreateGeofenceRequest(BaseModel):
    name: str
    latitude: float
    longitude: float
    radius: int = 100
    enabled: bool = True


class UpdateGeofenceRequest(BaseModel):
    name: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    radius: int | None = None
    enabled: bool | None = None


@router.get("/geofences", response_model=list[GeofenceResponse])
async def get_user_geofences(
    user_id: int = Query(..., description="User ID"),
):
    """
    Get all geofences for a user.
    """
    db_conn = connect(dsn=os.getenv("DATABASE_URI"))
    geofences = get_geofences_by_user_id(db_conn=db_conn, user_id=user_id)

    return [
        GeofenceResponse(
            geofence_id=gf.geofence_id,
            user_id=gf.user_id,
            name=gf.name,
            latitude=gf.latitude,
            longitude=gf.longitude,
            radius=gf.radius,
            enabled=gf.enabled,
        )
        for gf in geofences
    ]


@router.post("/geofences", response_model=GeofenceResponse, status_code=status.HTTP_201_CREATED)
async def create_user_geofence(
    request: CreateGeofenceRequest,
    user_id: int = Query(..., description="User ID"),
):
    """
    Create a new geofence for a user.
    """
    db_conn = connect(dsn=os.getenv("DATABASE_URI"))
    
    geofence = create_geofence(
        db_conn=db_conn,
        user_id=user_id,
        name=request.name,
        latitude=request.latitude,
        longitude=request.longitude,
        radius=request.radius,
        enabled=request.enabled,
    )

    return GeofenceResponse(
        geofence_id=geofence.geofence_id,
        user_id=geofence.user_id,
        name=geofence.name,
        latitude=geofence.latitude,
        longitude=geofence.longitude,
        radius=geofence.radius,
        enabled=geofence.enabled,
    )


@router.put("/geofences/{geofence_id}", response_model=GeofenceResponse)
async def update_user_geofence(
    geofence_id: int,
    request: UpdateGeofenceRequest,
    user_id: int = Query(..., description="User ID for authorization"),
):
    """
    Update a geofence. User must own the geofence.
    """
    db_conn = connect(dsn=os.getenv("DATABASE_URI"))
    
    # Verify the geofence belongs to the user
    existing = get_geofence(db_conn=db_conn, geofence_id=geofence_id)
    if existing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Geofence not found",
        )
    if existing.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Geofence does not belong to this user",
        )

    geofence = update_geofence(
        db_conn=db_conn,
        geofence_id=geofence_id,
        name=request.name,
        latitude=request.latitude,
        longitude=request.longitude,
        radius=request.radius,
        enabled=request.enabled,
    )

    return GeofenceResponse(
        geofence_id=geofence.geofence_id,
        user_id=geofence.user_id,
        name=geofence.name,
        latitude=geofence.latitude,
        longitude=geofence.longitude,
        radius=geofence.radius,
        enabled=geofence.enabled,
    )


@router.delete("/geofences/{geofence_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user_geofence(
    geofence_id: int,
    user_id: int = Query(..., description="User ID for authorization"),
):
    """
    Delete a geofence. User must own the geofence.
    """
    db_conn = connect(dsn=os.getenv("DATABASE_URI"))
    
    # Verify the geofence belongs to the user
    existing = get_geofence(db_conn=db_conn, geofence_id=geofence_id)
    if existing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Geofence not found",
        )
    if existing.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Geofence does not belong to this user",
        )

    delete_geofence(db_conn=db_conn, geofence_id=geofence_id)
    return None


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
