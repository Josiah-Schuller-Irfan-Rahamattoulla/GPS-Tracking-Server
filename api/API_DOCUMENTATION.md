# GPS Tracking Server API Documentation

## Overview

The GPS Tracking Server API is a FastAPI-based service for managing GPS tracking devices, users, and location data. The API provides endpoints for device registration, user authentication, GPS data submission, and data retrieval.

**Base URL:** TBD

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
  "control_1": true,
  "control_2": false,
  "control_3": null,
  "control_4": null
}
```

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
Associate a device with a user account.

**Headers:**
- `Access-Token`: Device access token

**Request Body:**
```json
{
  "device_id": 12345,
  "user_id": 1
}
```

**Response:**
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
  "timestamp": "2025-08-07T14:30:00Z"
}
```

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
    "control_1": true,
    "control_2": false,
    "control_3": null,
    "control_4": null
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
      "longitude": -122.4194
    },
    {
      "device_id": 12345,
      "time": "2025-08-07T14:31:00Z",
      "latitude": 37.7750,
      "longitude": -122.4195
    }
  ]
}
```

**Status Codes:**
- `200`: GPS data retrieved successfully
- `401`: Invalid user access token
- `400`: Invalid time range (end_time must be greater than start_time)

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
