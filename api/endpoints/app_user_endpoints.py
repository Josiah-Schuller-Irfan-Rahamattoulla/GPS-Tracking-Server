from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

from db.database import PGDatabase
from db.devices import get_devices_by_user_id
from db.gps_data import get_gps_data
from db.models import GPSData
from db.users import get_user, get_user_by_email, create_user, verify_user_password

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
    db_conn = PGDatabase.connect_to_db()
    
    # Check if user already exists
    existing_user = get_user_by_email(db_conn=db_conn.connection, email_address=request.email_address)
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email address already exists"
        )
    
    # Create new user
    try:
        new_user = create_user(
            db_conn=db_conn.connection,
            email_address=request.email_address,
            phone_number=request.phone_number,
            name=request.name,
            password=request.password
        )
        
        return AuthResponse(
            user_id=new_user.user_id,
            email_address=new_user.email_address,
            phone_number=new_user.phone_number,
            name=new_user.name,
            access_token=new_user.access_token
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user: {str(e)}"
        )


@auth_router.post("/login", response_model=AuthResponse)
async def login(request: LoginRequest):
    """
    Endpoint to authenticate a user and return their access token.
    """
    db_conn = PGDatabase.connect_to_db()
    
    # Verify user credentials
    user = verify_user_password(
        db_conn=db_conn.connection,
        email_address=request.email_address,
        password=request.password
    )
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email address or password"
        )
    
    return AuthResponse(
        user_id=user.user_id,
        email_address=user.email_address,
        phone_number=user.phone_number,
        name=user.name,
        access_token=user.access_token
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
    db_conn = PGDatabase.connect_to_db()
    user = get_user(db_conn=db_conn.connection, user_id=user_id)

    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

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
    db_conn = PGDatabase.connect_to_db()

    devices = get_devices_by_user_id(db_conn=db_conn.connection, user_id=user_id)

    return [AppDeviceResponse(
        device_id=device.device_id,
        sms_number=device.sms_number,
        control_1=device.control_1,
        control_2=device.control_2,
        control_3=device.control_3,
        control_4=device.control_4,
    ) for device in devices]


class AppGPSDataResponse(BaseModel):
    gps_data: list[GPSData]

@router.get("/GPSData", response_model=AppGPSDataResponse)
async def get_device_gps_data(
    user_id: int = Query(..., description="User ID"),  # Required for authorisation
    device_id: int = Query(..., description="Device ID"),
    start_time: datetime = Query(..., description="Start time of the GPS data to fetch"),
    end_time: datetime = Query(..., description="End time of the GPS data to fetch"),
):
    """
    Endpoint to receive GPS data from a device.
    """
    if end_time <= start_time:
        raise ValueError('end_time must be greater than start_time')

    db_conn = PGDatabase.connect_to_db()

    gps_data = get_gps_data(
        db_conn=db_conn.connection,
        device_id=device_id,
        start_time=start_time,
        end_time=end_time,
    )

    return AppGPSDataResponse(
        gps_data=gps_data,
    )
