from datetime import datetime

from fastapi import APIRouter
from pydantic import BaseModel

from db.database import PGDatabase
from db.gps_data import add_gps_data

router = APIRouter()

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
        longitude=device_data.longitude
    )    

    return DeviceDataResponse(
        success=True,
        message="GPS data saved successfully",
    )
