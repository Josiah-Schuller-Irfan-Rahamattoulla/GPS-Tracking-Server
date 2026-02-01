import os
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, Security, status
from fastapi.security import APIKeyHeader
from psycopg2 import connect
from psycopg2 import IntegrityError
from pydantic import BaseModel

from db.devices import create_device, get_device
from db.gps_data import add_gps_data

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
    """
    db_conn = connect(dsn=os.getenv("DATABASE_URI"))

    ts = device_data.timestamp
    if ts.year < 2020:
        ts = datetime.now(timezone.utc)

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
    db_conn = connect(dsn=os.getenv("DATABASE_URI"))

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
