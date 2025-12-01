# Missing Server Features for Concurrent Access

This document outlines the missing server features needed for concurrent access across:
- **Mobile App** (React Native)
- **Web Dashboard** (React/Expo)
- **Hardware Tracker** (nRF9151)

## Critical Missing Features

### 1. GPS Data Schema Extensions

**Current State:** Database only stores `latitude` and `longitude`

**Missing Fields:**
- `speed` (REAL) - Vehicle speed in km/h
- `heading` (REAL) - Compass heading in degrees (0-360)
- `trip_active` (BOOLEAN) - Hardware IMU-detected trip status

**Required Changes:**
```sql
ALTER TABLE gps_data 
ADD COLUMN speed REAL,
ADD COLUMN heading REAL,
ADD COLUMN trip_active BOOLEAN DEFAULT FALSE;

CREATE INDEX idx_gps_data_trip_active ON gps_data(device_id, trip_active) WHERE trip_active = TRUE;
```

**Impact:** Mobile app and web dashboard expect speed/heading, hardware sends `trip_active` flag

---

### 2. Device Name Management

**Current State:** Devices table has no `name` field

**Missing:**
- `name` (VARCHAR) - User-friendly device name

**Required Changes:**
```sql
ALTER TABLE devices ADD COLUMN name VARCHAR(100);
```

**Impact:** Both apps display device names, currently showing device_id instead

---

### 3. Missing API Endpoints

#### 3.1 Device Controls Update Endpoint

**Missing:** `PUT /v1/devices/{device_id}/controls`

**Expected by:** Web dashboard (kill switch control)

**Required Implementation:**
```python
@router.put("/devices/{device_id}/controls")
async def update_device_controls(
    device_id: int,
    user_id: int = Query(...),
    control_1: bool | None = None,
    control_2: bool | None = None,
    control_3: bool | None = None,
    control_4: bool | None = None,
):
    """Update device control flags (kill switch, etc.)"""
    # Verify user owns device
    # Update device controls
    # Return updated device
```

**Impact:** Web dashboard cannot remotely control kill switch

---

#### 3.2 Get Single Device Endpoint

**Missing:** `GET /v1/devices/{device_id}`

**Expected by:** Web dashboard (device details, kill switch sync)

**Required Implementation:**
```python
@router.get("/devices/{device_id}")
async def get_device(
    device_id: int,
    user_id: int = Query(...),
):
    """Get single device details including controls"""
    # Verify user owns device
    # Return device with controls
```

**Impact:** Cannot sync kill switch state or get device details

---

#### 3.3 Trip Status Endpoint

**Missing:** `GET /v1/tripStatus` or `GET /v1/devices/{device_id}/trip`

**Expected by:** Web dashboard

**Required Implementation:**
```python
@router.get("/devices/{device_id}/trip")
async def get_device_trip_status(
    device_id: int,
    user_id: int = Query(...),
):
    """Get current trip status from hardware IMU detection"""
    # Get latest GPS data with trip_active flag
    # Return trip status
```

**Impact:** Cannot display hardware-detected trip status

---

#### 3.4 Geofences CRUD Endpoints

**Missing:** Complete geofence management

**Expected by:** Both mobile app and web dashboard

**Required Implementation:**
- `GET /v1/geofences` - List all geofences for user
- `POST /v1/geofences` - Create geofence
- `PUT /v1/geofences/{geofence_id}` - Update geofence
- `DELETE /v1/geofences/{geofence_id}` - Delete geofence

**Database Schema Needed:**
```sql
CREATE TABLE geofences (
    geofence_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    name VARCHAR(100) NOT NULL,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    radius REAL NOT NULL DEFAULT 100, -- meters
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE INDEX idx_geofences_user ON geofences(user_id);
```

**Impact:** Geofences cannot be persisted or shared across devices

---

### 4. Enhanced GPS Data Endpoint

**Current:** `/v1/sendGPSData` only accepts basic fields

**Missing:** Support for `speed`, `heading`, `trip_active`

**Required Changes:**
```python
class DeviceData(BaseModel):
    device_id: int
    latitude: float
    longitude: float
    timestamp: datetime
    speed: float | None = None  # NEW
    heading: float | None = None  # NEW
    trip_active: bool | None = None  # NEW
```

**Impact:** Hardware and mobile app send additional data that's ignored

---

### 5. Concurrent Access Features

#### 5.1 Device Control Conflict Resolution

**Issue:** Multiple clients (web + mobile) can update device controls simultaneously

**Missing:**
- Optimistic locking (version field)
- Last-write-wins with timestamp
- Conflict detection and resolution

**Recommended:**
```sql
ALTER TABLE devices ADD COLUMN control_version INTEGER DEFAULT 0;
ALTER TABLE devices ADD COLUMN controls_updated_at TIMESTAMPTZ;
```

---

#### 5.2 Real-time Updates (Optional but Recommended)

**Missing:** WebSocket or Server-Sent Events (SSE) for real-time updates

**Use Cases:**
- Live GPS position updates without polling
- Instant kill switch state changes
- Geofence entry/exit notifications
- Device status changes

**Implementation Options:**
- FastAPI WebSockets
- Server-Sent Events (SSE) - simpler, one-way
- Polling (current) - works but inefficient

**Impact:** All clients must poll, causing:
- High server load
- Delayed updates
- Battery drain on mobile

---

### 6. Device Heartbeat/Status Tracking

**Missing:** Device online/offline status

**Current:** Status inferred from GPS data age

**Recommended:**
```sql
CREATE TABLE device_heartbeats (
    device_id INTEGER PRIMARY KEY,
    last_heartbeat TIMESTAMPTZ NOT NULL,
    last_gps_time TIMESTAMPTZ,
    battery_level INTEGER, -- 0-100
    signal_strength INTEGER, -- 0-5
    FOREIGN KEY (device_id) REFERENCES devices(device_id) ON DELETE CASCADE
);

CREATE INDEX idx_heartbeats_time ON device_heartbeats(last_heartbeat);
```

**New Endpoint:**
```python
@router.post("/devices/{device_id}/heartbeat")
async def device_heartbeat(
    device_id: int,
    battery_level: int | None = None,
    signal_strength: int | None = None,
):
    """Update device heartbeat (called periodically by hardware)"""
```

**Impact:** Better status detection, battery monitoring

---

### 7. Geofence Event Logging

**Missing:** Log when vehicles enter/exit geofences

**Recommended:**
```sql
CREATE TABLE geofence_events (
    event_id SERIAL PRIMARY KEY,
    device_id INTEGER NOT NULL,
    geofence_id INTEGER NOT NULL,
    event_type VARCHAR(10) NOT NULL, -- 'enter' or 'exit'
    event_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    FOREIGN KEY (device_id) REFERENCES devices(device_id) ON DELETE CASCADE,
    FOREIGN KEY (geofence_id) REFERENCES geofences(geofence_id) ON DELETE CASCADE
);

CREATE INDEX idx_geofence_events_device ON geofence_events(device_id, event_time DESC);
CREATE INDEX idx_geofence_events_geofence ON geofence_events(geofence_id, event_time DESC);
```

**Impact:** Historical geofence alerts, compliance tracking

---

## Priority Implementation Order

### Phase 1: Critical (Blocks Core Functionality)
1. ✅ GPS data schema extensions (speed, heading, trip_active)
2. ✅ Device name field
3. ✅ Enhanced `/v1/sendGPSData` to accept new fields
4. ✅ `PUT /v1/devices/{device_id}/controls` endpoint
5. ✅ `GET /v1/devices/{device_id}` endpoint
6. ✅ `GET /v1/devices/{device_id}/trip` endpoint

### Phase 2: High Priority (Enables Full Features)
7. ✅ Geofences table and CRUD endpoints
8. ✅ Device control conflict resolution

### Phase 3: Nice to Have (Performance/Optimization)
9. ⏳ Device heartbeat/status tracking
10. ⏳ Geofence event logging
11. ⏳ WebSocket/SSE for real-time updates

---

## Testing Checklist

After implementing, test:
- [ ] Hardware (nRF9151) can send GPS data with speed/heading/trip_active
- [ ] Mobile app can send GPS data with all fields
- [ ] Web dashboard can update device controls
- [ ] Web dashboard can read device controls
- [ ] Geofences persist across app restarts
- [ ] Geofences sync between mobile and web
- [ ] Multiple clients can update controls without conflicts
- [ ] Trip status reflects hardware IMU detection

---

## Notes

- All endpoints should verify user owns device before allowing access
- Device controls should be readable by hardware (for kill switch enforcement)
- Consider rate limiting for GPS data submissions
- Add database indexes for performance with large datasets
- Consider partitioning `gps_data` table by time for better performance


