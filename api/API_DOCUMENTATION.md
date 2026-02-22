# GPS Tracking Server API Documentation

## Overview

The GPS Tracking Server API is a FastAPI-based service for managing GPS tracking devices, users, and location data. The API provides endpoints for device registration, user authentication, GPS data submission, and data retrieval.

**Base URL:** https://gpstracking.josiahschuller.au

## Authentication

The API uses two types of authentication:

### 1. Device Authentication
- **Header:** `Access-Token`
- **Description:** Used by GPS tracking devices to authenticate API calls
- **Required for:** Device data submission and device-to-user registration

### 2. User Authentication  
- **Header:** `Access-Token`
- **Description:** Used by mobile/web applications to authenticate user API calls
- **Required for:** User data retrieval and device management

## API Endpoints

### Authentication Endpoints

#### POST `/v1/signup`
Create a new user account.

**Request Body:**
```json
{
  "email_address": "user@example.com",
  "phone_number": "+1234567890",
  "name": "John Doe",
  "password": "securepassword"
}
```

**Response:**
```json
{
  "user_id": 1,
  "email_address": "user@example.com",
  "phone_number": "+1234567890",
  "name": "John Doe",
  "access_token": "user_access_token_here"
}
```

**Status Codes:**
- `200`: User created successfully
- `409`: User with email already exists
- `500`: Internal server error

---

#### POST `/v1/login`
Authenticate a user and retrieve access token.

**Request Body:**
```json
{
  "email_address": "user@example.com",
  "password": "securepassword"
}
```

**Response:**
```json
{
  "user_id": 1,
  "email_address": "user@example.com",
  "phone_number": "+1234567890",
  "name": "John Doe",
  "access_token": "user_access_token_here"
}
```

**Status Codes:**
- `200`: Login successful
- `401`: Invalid credentials

---

### Device Registration Endpoints

#### POST `/v1/registerDevice`
Register a new GPS tracking device.

**Request Body:**
```json
{
  "device_id": 12345,
  "access_token": "device_access_token_here",
  "sms_number": "+1234567890",
  "name": "My Vehicle",
  "control_1": true,
  "control_2": false,
  "control_3": null,
  "control_4": null
}
```

**Notes:**
- `name`: User-friendly device name (optional)
- `control_*`: Initial control flag states (optional)

**Response:**
```json
{
  "success": true,
  "message": "Device registered successfully"
}
```

**Status Codes:**
- `200`: Device registered successfully
- `409`: Device with ID already exists

---

#### POST `/v1/registerDeviceToUser`
Link an existing device to a user account. Requires the device's pairing code (`access_token`) so only someone with the sticker/device can claim it.

**Headers:**
- `Access-Token`: **User** access token

**Query:**
- `user_id`: User ID to link the device to

**Request Body:**
```json
{
  "device_id": 12345,
  "access_token": "pairing-code-from-sticker"
}
```

**Response:**
- `200`: Device linked successfully
- `403`: Invalid pairing code for this device
- `404`: Device not found

```json
{
  "success": true,
  "message": "Device registered to user successfully"
}
```

**Status Codes:**
- `200`: Device associated with user successfully
- `401`: Invalid device access token
- `400`: Missing device_id or user_id

---

### Device Data Endpoints

#### POST `/v1/sendGPSData`
Submit GPS location data from a device.

**Headers:**
- `Access-Token`: Device access token

**Request Body:**
```json
{
  "device_id": 12345,
  "latitude": 37.7749,
  "longitude": -122.4194,
  "timestamp": "2025-08-07T14:30:00Z",
  "speed": 65.5,
  "heading": 180.0,
  "trip_active": true
}
```

**Notes:**
- `speed`: Vehicle speed in km/h (optional)
- `heading`: Compass heading in degrees 0-360 (optional)
- `trip_active`: Hardware IMU-detected trip status (optional)

**Response:**
```json
{
  "success": true,
  "message": "GPS data saved successfully",
  "data": null
}
```

**Status Codes:**
- `200`: GPS data saved successfully
- `401`: Invalid device access token
- `400`: Missing or invalid data

---

#### GET `/v1/getDeviceControls`
Retrieve device control settings (called by device firmware).

**Headers:**
- `Access-Token`: Device access token

**Query Parameters:**
- `device_id` (required): Device ID

**Response:**
```json
{
  "device_id": 12345,
  "control_1": true,
  "control_2": false,
  "control_3": null,
  "control_4": null,
  "control_version": 2,
  "controls_updated_at": "2025-08-07T14:30:00Z"
}
```

**Status Codes:**
- `200`: Device controls retrieved successfully
- `401`: Invalid device access token
- `404`: Device not found

---

### User Data Endpoints

#### GET `/v1/user`
Retrieve user information.

**Headers:**
- `Access-Token`: User access token

**Query Parameters:**
- `user_id` (required): User ID

**Response:**
```json
{
  "user_id": 1,
  "email_address": "user@example.com",
  "phone_number": "+1234567890",
  "name": "John Doe"
}
```

**Status Codes:**
- `200`: User data retrieved successfully
- `401`: Invalid user access token
- `404`: User not found

---

#### GET `/v1/devices`
Retrieve devices associated with a user.

**Headers:**
- `Access-Token`: User access token

**Query Parameters:**
- `user_id` (required): User ID

**Response:**
```json
[
  {
    "device_id": 12345,
    "sms_number": "+1234567890",
    "name": "My Vehicle",
    "control_1": true,
    "control_2": false,
    "control_3": null,
    "control_4": null,
    "control_version": 2,
    "controls_updated_at": "2025-08-07T14:30:00Z"
  }
]
```

**Status Codes:**
- `200`: Devices retrieved successfully
- `401`: Invalid user access token

---

#### GET `/v1/GPSData`
Retrieve GPS data for a specific device within a time range.

**Headers:**
- `Access-Token`: User access token

**Query Parameters:**
- `user_id` (required): User ID (for authorization)
- `device_id` (required): Device ID
- `start_time` (required): Start time in ISO format (e.g., "2025-08-07T00:00:00Z")
- `end_time` (required): End time in ISO format (e.g., "2025-08-07T23:59:59Z")

**Response:**
```json
{
  "gps_data": [
    {
      "device_id": 12345,
      "time": "2025-08-07T14:30:00Z",
      "latitude": 37.7749,
      "longitude": -122.4194,
      "speed": 65.5,
      "heading": 180.0,
      "trip_active": true
    },
    {
      "device_id": 12345,
      "time": "2025-08-07T14:31:00Z",
      "latitude": 37.7750,
      "longitude": -122.4195,
      "speed": 64.2,
      "heading": 180.0,
      "trip_active": true
    }
  ]
}
```

**Status Codes:**
- `200`: GPS data retrieved successfully
- `401`: Invalid user access token
- `400`: Invalid time range (end_time must be greater than start_time)

---

#### GET `/v1/devices/{device_id}`
Retrieve a single device by ID with control settings.

**Headers:**
- `Access-Token`: User access token

**Query Parameters:**
- `user_id` (required): User ID (for authorization)

**Response:**
```json
{
  "device_id": 12345,
  "sms_number": "+1234567890",
  "name": "My Vehicle",
  "control_1": true,
  "control_2": false,
  "control_3": null,
  "control_4": null,
  "control_version": 2,
  "controls_updated_at": "2025-08-07T14:30:00Z"
}
```

**Status Codes:**
- `200`: Device retrieved successfully
- `401`: Invalid user access token
- `404`: Device not found or not owned by user

---

#### PUT `/v1/devices/{device_id}/controls`
Update device control flags (kill switch, etc.) with optimistic locking support.

**Headers:**
- `Access-Token`: User access token

**Query Parameters:**
- `user_id` (required): User ID (for authorization)

**Request Body:**
```json
{
  "control_1": true,
  "control_2": false,
  "control_3": null,
  "control_4": null,
  "expected_version": 2
}
```

**Notes:**
- `expected_version` is optional and used for optimistic locking to prevent concurrent update conflicts
- At least one control field must be provided

**Response:**
```json
{
  "device_id": 12345,
  "sms_number": "+1234567890",
  "name": "My Vehicle",
  "control_1": true,
  "control_2": false,
  "control_3": null,
  "control_4": null,
  "control_version": 3,
  "controls_updated_at": "2025-08-07T14:35:00Z"
}
```

**Status Codes:**
- `200`: Device controls updated successfully
- `401`: Invalid user access token
- `404`: Device not found or not owned by user or version conflict

---

#### GET `/v1/devices/{device_id}/trip`
Get current trip status from hardware IMU detection.

**Headers:**
- `Access-Token`: User access token

**Query Parameters:**
- `user_id` (required): User ID (for authorization)

**Response:**
```json
{
  "trip_active": true,
  "last_trip_time": "2025-08-07T14:15:00Z",
  "last_gps_time": "2025-08-07T14:35:00Z"
}
```

**Status Codes:**
- `200`: Trip status retrieved successfully
- `401`: Invalid user access token
- `404`: Device not found or not owned by user

---

### Geofence Endpoints

#### GET `/v1/geofences`
Retrieve all geofences for a user.

**Headers:**
- `Access-Token`: User access token

**Query Parameters:**
- `user_id` (required): User ID

**Response:**
```json
[
  {
    "geofence_id": 1,
    "user_id": 1,
    "name": "Home",
    "latitude": 37.7749,
    "longitude": -122.4194,
    "radius": 500.0,
    "enabled": true,
    "created_at": "2025-08-01T10:00:00Z"
  },
  {
    "geofence_id": 2,
    "user_id": 1,
    "name": "Work",
    "latitude": 37.7850,
    "longitude": -122.4095,
    "radius": 300.0,
    "enabled": true,
    "created_at": "2025-08-02T12:00:00Z"
  }
]
```

**Status Codes:**
- `200`: Geofences retrieved successfully
- `401`: Invalid user access token

---

#### POST `/v1/geofences`
Create a new geofence.

**Headers:**
- `Access-Token`: User access token

**Query Parameters:**
- `user_id` (required): User ID

**Request Body:**
```json
{
  "name": "Home",
  "latitude": 37.7749,
  "longitude": -122.4194,
  "radius": 500.0,
  "enabled": true
}
```

**Validation:**
- Latitude must be between -90 and 90
- Longitude must be between -180 and 180
- Radius must be greater than 0 (in meters)

**Response:**
```json
{
  "geofence_id": 1,
  "user_id": 1,
  "name": "Home",
  "latitude": 37.7749,
  "longitude": -122.4194,
  "radius": 500.0,
  "enabled": true,
  "created_at": "2025-08-07T14:30:00Z"
}
```

**Status Codes:**
- `200`: Geofence created successfully
- `401`: Invalid user access token
- `400`: Invalid geofence data

---

#### PUT `/v1/geofences/{geofence_id}`
Update an existing geofence.

**Headers:**
- `Access-Token`: User access token

**Query Parameters:**
- `user_id` (required): User ID

**Request Body:**
```json
{
  "name": "Home Sweet Home",
  "latitude": 37.7749,
  "longitude": -122.4194,
  "radius": 600.0,
  "enabled": false
}
```

**Notes:**
- All fields are optional. Only provided fields will be updated.

**Response:**
```json
{
  "geofence_id": 1,
  "user_id": 1,
  "name": "Home Sweet Home",
  "latitude": 37.7749,
  "longitude": -122.4194,
  "radius": 600.0,
  "enabled": false,
  "created_at": "2025-08-07T14:30:00Z"
}
```

**Status Codes:**
- `200`: Geofence updated successfully
- `401`: Invalid user access token
- `404`: Geofence not found or not owned by user
- `400`: Invalid geofence data

---

#### DELETE `/v1/geofences/{geofence_id}`
Delete a geofence.

**Headers:**
- `Access-Token`: User access token

**Query Parameters:**
- `user_id` (required): User ID

**Response:**
```json
{
  "success": true,
  "message": "Geofence deleted successfully"
}
```

**Status Codes:**
- `200`: Geofence deleted successfully
- `401`: Invalid user access token
- `404`: Geofence not found or not owned by user

---



## Error Handling

The API returns standard HTTP status codes and JSON error responses:

```json
{
  "detail": "Error message description"
}
```

### Common Error Codes
- `400`: Bad Request - Invalid or missing parameters
- `401`: Unauthorized - Invalid or missing access token
- `404`: Not Found - Resource not found
- `409`: Conflict - Resource already exists

## Data Format Notes

- **Timestamps:** All timestamps should be in ISO 8601 format (UTC)
- **Coordinates:** Latitude and longitude should be decimal degrees
- **Phone Numbers:** Should include country code (e.g., +1234567890)
- **Email Addresses:** Must be valid email format
- **Device IDs:** Integer values, must be unique per device
- **User IDs:** Integer values, automatically generated
