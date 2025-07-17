from datetime import datetime
from pydantic import BaseModel


class Device(BaseModel):
    # Row of "devices" table
    device_id: int
    sms_number: str
    created_at: datetime
    control_1: bool
    control_2: bool
    control_3: bool
    control_4: bool

class GPSData(BaseModel):
    # Row of "gps_data" table
    device_id: int
    time: datetime
    latitude: float
    longitude: float

class User(BaseModel):
    # Row of "users" table
    user_id: int
    email_address: str
    phone_number: str
    name: str
    salt: str
    hashed_password: str
    access_token: str
    created_at: datetime

class UserDevice(BaseModel):
    # Row of "users_devices" table
    user_id: int
    device_id: int
