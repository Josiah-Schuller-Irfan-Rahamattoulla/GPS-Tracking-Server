from datetime import datetime
from pydantic import BaseModel


class Device(BaseModel):
    # Row of "devices" table
    device_id: int
    access_token: str
    sms_number: str
    created_at: datetime
    remote_viewing: bool = False
    last_viewed_at: datetime | None = None
    name: str | None = None
    control_1: bool | None
    control_2: bool | None
    control_3: bool | None
    control_4: bool | None
    control_version: int | None = None
    last_applied_control_version: int | None = 0
    controls_updated_at: datetime | None = None


class GPSData(BaseModel):
    # Row of "gps_data" table
    device_id: int
    time: datetime
    latitude: float
    longitude: float
    speed: float | None = None
    heading: float | None = None
    trip_active: bool | None = None


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


class Geofence(BaseModel):
    # Row of "geofences" table
    geofence_id: int
    user_id: int
    name: str
    latitude: float
    longitude: float
    radius: float
    enabled: bool
    created_at: datetime


class GeofenceBreachEvent(BaseModel):
    # Row of "geofence_breach_events" table
    event_id: int
    device_id: int
    geofence_id: int
    user_id: int
    event_type: str  # 'ENTERED' or 'EXITED'
    latitude: float
    longitude: float
    event_time: datetime
    notification_sent: bool
    notification_method: str | None = None
    notification_sent_at: datetime | None = None
