from datetime import datetime

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from db.database import PGDatabase
from db.devices import create_device, create_user_device_row, get_device
from db.gps_data import add_gps_data

router = APIRouter()

device_registration_router = APIRouter()  # Router for device registration endpoints


class DeviceData(BaseModel):
    device_id: int
    latitude: float
    longitude: float
    timestamp: datetime


class DeviceDataResponse(BaseModel):
    success: bool
    message: str
    data: DeviceData | None = None


@router.post("/sendGPSData", response_model=DeviceDataResponse)
async def send_gps_data(device_data: DeviceData):
    """
    Endpoint to receive GPS data from a device.
    """
    db_conn = PGDatabase.connect_to_db()

    add_gps_data(
        db_conn=db_conn.connection,
        device_id=device_data.device_id,
        timestamp=device_data.timestamp,
        latitude=device_data.latitude,
        longitude=device_data.longitude,
    )

    return DeviceDataResponse(
        success=True,
        message="GPS data saved successfully",
    )


class DeviceRegistrationData(BaseModel):
    device_id: int
    access_token: str
    sms_number: str
    control_1: bool | None = None
    control_2: bool | None = None
    control_3: bool | None = None
    control_4: bool | None = None


@device_registration_router.post("/registerDevice")
async def register_device(device_data: DeviceRegistrationData):
    """
    Endpoint to register a new device.
    """
    db_conn = PGDatabase.connect_to_db()

    # Check if device already exists
    existing_device = get_device(
        db_conn=db_conn.connection, device_id=device_data.device_id
    )
    if existing_device:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Device with this ID already exists",
        )

    create_device(
        db_conn=db_conn.connection,
        device_id=device_data.device_id,
        access_token=device_data.access_token,
        sms_number=device_data.sms_number,
        control_1=device_data.control_1,
        control_2=device_data.control_2,
        control_3=device_data.control_3,
        control_4=device_data.control_4,
    )

    return {"success": True, "message": "Device registered successfully"}


class UserDeviceRegistrationData(BaseModel):
    device_id: int
    user_id: int


@router.post("/registerDeviceToUser")
async def register_device_to_user(registration_data: UserDeviceRegistrationData):
    """
    Endpoint to register a device to a user.
    """
    db_conn = PGDatabase.connect_to_db()

    create_user_device_row(
        db_conn=db_conn.connection,
        user_id=registration_data.user_id,
        device_id=registration_data.device_id,
    )

    return {"success": True, "message": "Device registered to user successfully"}
