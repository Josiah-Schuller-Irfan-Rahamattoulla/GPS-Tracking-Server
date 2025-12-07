# Server Setup and Testing Guide

## Prerequisites

- Python 3.8+
- PostgreSQL database
- Docker (for local development)

## Setup Steps

### 1. Run Database Migration

First, apply the database migration to add new features:

```bash
# Connect to your PostgreSQL database
psql -U your_username -d your_database_name

# Run the migration
\i database/migration_001_add_features.sql

# Or from command line:
psql -U your_username -d your_database_name -f database/migration_001_add_features.sql
```

**Migration adds:**
- GPS data extensions: `speed`, `heading`, `trip_active` columns
- Device `name` field
- Device control versioning: `control_version`, `controls_updated_at`
- Geofences table with full CRUD support

### 2. Install Dependencies

```bash
cd api
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip sync requirements.txt
```

### 3. Set Environment Variables

Create a `.env` file in the `api` directory:

```env
DATABASE_URI=postgresql://username:password@localhost:5432/database_name
```

### 4. Start the Server

```bash
cd api
python main.py
```

Server will start on `http://localhost:8000`

## Testing

### Run Automated Tests

```bash
# Install requests if not already installed
pip install requests

# Run test script
python test_new_endpoints.py --base-url http://localhost:8000
```

The test script will:
1. ✅ Create a test user
2. ✅ Register a test device with name
3. ✅ Link device to user
4. ✅ Send GPS data with speed/heading/trip_active
5. ✅ Get single device details
6. ✅ Update device controls (kill switch)
7. ✅ Get trip status
8. ✅ Create geofence
9. ✅ Get all geofences
10. ✅ Update geofence
11. ✅ Get user devices (with names)
12. ✅ Get GPS data (with speed/heading)
13. ✅ Delete geofence

### Manual Testing with cURL

#### 1. Create User
```bash
curl -X POST "http://localhost:8000/v1/signup" \
  -H "Content-Type: application/json" \
  -d '{
    "email_address": "test@example.com",
    "phone_number": "+61400000000",
    "name": "Test User",
    "password": "testpass123"
  }'
```

#### 2. Register Device (with name)
```bash
curl -X POST "http://localhost:8000/v1/registerDevice" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": 12345,
    "access_token": "device_token_12345",
    "sms_number": "+61400000001",
    "name": "My Vehicle"
  }'
```

#### 3. Send GPS Data (with speed/heading/trip_active)
```bash
curl -X POST "http://localhost:8000/v1/sendGPSData" \
  -H "Access-Token: device_token_12345" \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": 12345,
    "latitude": -37.8136,
    "longitude": 144.9631,
    "timestamp": "2025-01-15T10:30:00Z",
    "speed": 65.5,
    "heading": 180.0,
    "trip_active": true
  }'
```

#### 4. Get Single Device
```bash
curl -X GET "http://localhost:8000/v1/devices/12345?user_id=1" \
  -H "Access-Token: YOUR_USER_TOKEN"
```

#### 5. Update Device Controls
```bash
curl -X PUT "http://localhost:8000/v1/devices/12345/controls?user_id=1" \
  -H "Access-Token: YOUR_USER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "control_1": true,
    "control_2": true
  }'
```

#### 6. Get Trip Status
```bash
curl -X GET "http://localhost:8000/v1/devices/12345/trip?user_id=1" \
  -H "Access-Token: YOUR_USER_TOKEN"
```

#### 7. Create Geofence
```bash
curl -X POST "http://localhost:8000/v1/geofences?user_id=1" \
  -H "Access-Token: YOUR_USER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Home",
    "latitude": -37.8136,
    "longitude": 144.9631,
    "radius": 500.0,
    "enabled": true
  }'
```

#### 8. Get Geofences
```bash
curl -X GET "http://localhost:8000/v1/geofences?user_id=1" \
  -H "Access-Token: YOUR_USER_TOKEN"
```

## New Endpoints Summary

### Device Endpoints
- `GET /v1/devices/{device_id}` - Get single device with controls
- `PUT /v1/devices/{device_id}/controls` - Update device controls (kill switch)
- `GET /v1/devices/{device_id}/trip` - Get trip status from hardware

### Geofence Endpoints
- `GET /v1/geofences` - List all geofences for user
- `POST /v1/geofences` - Create new geofence
- `PUT /v1/geofences/{geofence_id}` - Update geofence
- `DELETE /v1/geofences/{geofence_id}` - Delete geofence

### Enhanced Endpoints
- `POST /v1/sendGPSData` - Now accepts `speed`, `heading`, `trip_active`
- `POST /v1/registerDevice` - Now accepts `name` field
- `GET /v1/devices` - Now returns `name`, `control_version`, `controls_updated_at`

## Database Schema Changes

### gps_data table
- Added: `speed REAL`
- Added: `heading REAL`
- Added: `trip_active BOOLEAN`

### devices table
- Added: `name VARCHAR(100)`
- Added: `control_version INTEGER` (for optimistic locking)
- Added: `controls_updated_at TIMESTAMPTZ`

### New geofences table
- `geofence_id` (PK)
- `user_id` (FK)
- `name`, `latitude`, `longitude`, `radius`, `enabled`
- `created_at`

## Verification Checklist

After setup, verify:
- [ ] Migration ran successfully (check tables exist)
- [ ] Server starts without errors
- [ ] Test script passes all tests
- [ ] GPS data with speed/heading/trip_active is stored
- [ ] Device names are saved and retrieved
- [ ] Device controls can be updated
- [ ] Trip status endpoint returns data
- [ ] Geofences can be created/updated/deleted
- [ ] Control versioning prevents conflicts

## Troubleshooting

### Migration Errors
- Ensure PostgreSQL version supports all SQL features
- Check database user has CREATE/ALTER permissions
- Verify foreign key constraints are satisfied

### Import Errors
- Ensure all dependencies are installed: `uv pip sync requirements.txt`
- Check Python version (3.8+)

### Authorization Errors
- Verify `Access-Token` header is set correctly
- Check user_id matches token owner
- Ensure device belongs to user (for device endpoints)

### Database Connection Errors
- Verify `DATABASE_URI` in `.env` is correct
- Check PostgreSQL is running
- Test connection: `psql $DATABASE_URI`

