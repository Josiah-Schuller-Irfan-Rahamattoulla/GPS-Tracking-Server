# Firmware Integration Plan

This document outlines planned improvements for the nRF9151 firmware to integrate with server-side features.

## Priority 1: A-GNSS Integration

### Current State
- ✅ Server has `/agnss` endpoint that proxies nRF Cloud A-GNSS data
- ❌ Firmware never calls the A-GNSS endpoint
- ❌ GPS cold start takes 30-60 seconds

### Goal
Reduce GPS Time-To-First-Fix (TTFF) from 30-60s to 5-10s by using A-GNSS data.

### Implementation Steps

#### 1. Add A-GNSS Request Function to server_driver.c

```c
/**
 * @brief Request A-GNSS data from server to speed up GPS acquisition
 * 
 * @param lat Approximate latitude (optional, can be 0)
 * @param lon Approximate longitude (optional, can be 0)
 * @param agnss_data Buffer to store A-GNSS data
 * @param agnss_data_len Size of buffer
 * @param response Response structure
 * @return 0 on success, negative error code on failure
 */
int server_driver_request_agnss(double lat, double lon,
                                 uint8_t *agnss_data,
                                 size_t agnss_data_len,
                                 server_driver_response_t *response);
```

**HTTP Request Format:**
```http
GET /v1/agnss?device_id=123456&lat=37.7749&lon=-122.4194
Access-Token: device_access_token
```

**Server Response:**
- Content-Type: `application/octet-stream`
- Body: Binary A-GNSS data (nRF Cloud format, passed through unchanged)

#### 2. Integrate with GNSS Driver (drivers/gnss.c)

```c
/**
 * @brief Load A-GNSS data into modem before GPS acquisition
 * 
 * @param agnss_data Binary A-GNSS data from server
 * @param agnss_data_len Length of A-GNSS data
 * @return 0 on success, negative error code on failure
 */
int gnss_load_agnss(const uint8_t *agnss_data, size_t agnss_data_len);
```

Use nRF SDK function: `nrf_modem_gnss_agps_write()`

#### 3. Update GPS Acquisition Flow

**Current Flow:**
1. GPS thread wakes up
2. Calls `nrf_modem_gnss_start()`
3. Waits for fix (30-60s)

**New Flow:**
1. GPS thread wakes up
2. If connected to server and A-GNSS not fetched in last 2 hours:
   - Request A-GNSS data from server
   - Load A-GNSS into modem
3. Call `nrf_modem_gnss_start()`
4. Get fix in 5-10s

**A-GNSS Caching:**
- Cache A-GNSS data for 2 hours (satellite ephemeris valid for ~2-4 hours)
- Use timestamp to track last A-GNSS fetch
- Re-fetch when expired or on power-up

#### 4. Configuration
Add to device configuration (via `CONFIG_` options or runtime):
```
CONFIG_ENABLE_AGNSS=y
CONFIG_AGNSS_CACHE_TIMEOUT_SEC=7200  # 2 hours
```

### Testing
1. Monitor GPS acquisition time before A-GNSS: expect 30-60s
2. Enable A-GNSS and monitor: expect 5-15s
3. Verify A-GNSS data is re-fetched after cache expiry
4. Test behavior when server is unreachable (should fall back to cold start)

### Benefits
- **5-10x faster GPS acquisition** (60s → 5-10s)
- **Better user experience** (faster location updates)
- **Lower power consumption** (shorter GPS on-time)

---

## Priority 2: Offline GPS Buffering

### Current State
- ❌ GPS points are lost if no LTE connection
- ❌ No retry mechanism for failed uploads
- ❌ No local storage for GPS data

### Goal
Buffer GPS coordinates locally when offline, upload when connection restored.

### Implementation Steps

#### 1. Add Flash Storage for GPS Points

Use Zephyr NVS (Non-Volatile Storage) or Flash Circular Buffer:

```c
#include <zephyr/fs/nvs.h>

#define GPS_BUFFER_MAX_POINTS 100  // Store up to 100 points
#define GPS_BUFFER_FLASH_ID 1

struct gps_buffer_entry {
    double latitude;
    double longitude;
    uint64_t timestamp;  // Unix timestamp
    float speed;         // Optional
    float heading;       // Optional
    bool trip_active;    // Optional
};
```

#### 2. Add Buffer Management Functions

```c
/**
 * @brief Add GPS point to offline buffer
 */
int gps_buffer_add(const struct gps_buffer_entry *entry);

/**
 * @brief Get number of buffered points
 */
int gps_buffer_count(void);

/**
 * @brief Get oldest buffered point
 */
int gps_buffer_get_oldest(struct gps_buffer_entry *entry);

/**
 * @brief Remove oldest buffered point
 */
int gps_buffer_remove_oldest(void);

/**
 * @brief Upload all buffered points to server
 */
int gps_buffer_upload_all(void);
```

#### 3. Update GPS Upload Logic

**Current Logic:**
```
1. Get GPS fix
2. Send to server immediately
3. If failed, discard data
```

**New Logic:**
```
1. Get GPS fix
2. Try to send to server
3. If failed:
   - Add to offline buffer
   - Log error
4. Periodically check buffer:
   - If buffer not empty and LTE connected:
     - Upload all buffered points
     - Clear buffer on success
```

#### 4. Add Batch Upload Endpoint

Server needs a batch upload endpoint:
```http
POST /v1/sendGPSDataBatch
Access-Token: device_token
Content-Type: application/json

{
  "device_id": 123456,
  "data_points": [
    {
      "latitude": 37.7749,
      "longitude": -122.4194,
      "timestamp": "2026-02-06T10:00:00Z",
      "speed": 25.5,
      "heading": 90.0,
      "trip_active": true
    },
    ...
  ]
}
```

#### 5. Configuration

```
CONFIG_ENABLE_GPS_BUFFER=y
CONFIG_GPS_BUFFER_MAX_POINTS=100
CONFIG_GPS_BUFFER_UPLOAD_INTERVAL_SEC=300  # Try every 5 min
```

### Testing
1. Disconnect LTE and take GPS readings → verify stored in flash
2. Reconnect LTE → verify points uploaded and buffer cleared
3. Fill buffer to max → verify oldest points dropped when full
4. Power cycle device → verify buffered points survive reboot

### Benefits
- **No data loss** during temporary network outages
- **Better reliability** for tracking in areas with poor coverage
- **Complete trip history** even with intermittent connectivity

---

## Priority 3: Adaptive Upload Frequency

### Current State
- ❌ GPS upload interval is fixed (e.g., every 30s)
- ❌ Wastes power when stationary
- ❌ May miss rapid movements

### Goal
Dynamically adjust GPS upload frequency based on motion state.

### Implementation

#### Motion States
```c
typedef enum {
    MOTION_STATE_STATIONARY,    // No movement detected
    MOTION_STATE_SLOW,          // Walking speed
    MOTION_STATE_MOVING,        // Normal driving
    MOTION_STATE_FAST           // High-speed movement
} motion_state_t;
```

#### Upload Intervals by State
```c
#define UPLOAD_INTERVAL_STATIONARY_SEC  300  // 5 minutes
#define UPLOAD_INTERVAL_SLOW_SEC        60   // 1 minute
#define UPLOAD_INTERVAL_MOVING_SEC      30   // 30 seconds
#define UPLOAD_INTERVAL_FAST_SEC        15   // 15 seconds
```

#### Motion Detection
Use existing IMU (LSM6DSOX accelerometer) to detect motion:
```c
/**
 * @brief Detect current motion state from IMU data
 */
motion_state_t detect_motion_state(void);
```

Algorithm:
1. Read accelerometer magnitude
2. Compare to thresholds:
   - < 0.1 m/s² → STATIONARY
   - 0.1-1.0 m/s² → SLOW
   - 1.0-3.0 m/s² → MOVING
   - > 3.0 m/s² → FAST

#### GPS Thread Update
```c
while (1) {
    motion_state_t state = detect_motion_state();
    int interval = get_upload_interval(state);
    
    // Get GPS fix
    acquire_gps();
    upload_gps_data();
    
    // Sleep based on motion state
    k_sleep(K_SECONDS(interval));
}
```

### Benefits
- **50-80% power savings** when stationary
- **Better tracking** during rapid movement
- **Extended battery life**

---

## Priority 4: Battery-Aware Transmission

### Current State
- ❌ Upload frequency doesn't consider battery level
- ❌ Device may die faster when battery low

### Goal
Reduce GPS frequency when battery is critically low.

### Implementation

```c
/**
 * @brief Get adjusted upload interval based on battery level
 */
int get_battery_adjusted_interval(int base_interval, float battery_pct) {
    if (battery_pct < 10.0) {
        return base_interval * 4;  // 4x slower when critical
    } else if (battery_pct < 20.0) {
        return base_interval * 2;  // 2x slower when low
    }
    return base_interval;
}
```

Example:
- Normal: 30s interval
- Battery < 20%: 60s interval
- Battery < 10%: 120s interval

### Benefits
- **Extended runtime** when battery low
- **Emergency tracking** preserved longer
- **Predictable behavior** (always functional, just slower)

---

## Priority 5: Firmware Version Reporting

### Current State
- ❌ Server doesn't know firmware version
- ❌ No way to track which devices need OTA updates

### Goal
Report firmware version to server on registration and periodically.

### Implementation

#### 1. Add Version to Device Registration

```c
// In server_driver.c
#define FIRMWARE_VERSION "1.0.0"

// Update registration JSON
"{"
"\"device_id\":%u,"
"\"access_token\":\"%s\","
"\"firmware_version\":\"%s\","
"\"sms_number\":\"%s\""
```

#### 2. Server Schema Update

Add column to `devices` table:
```sql
ALTER TABLE devices ADD COLUMN firmware_version VARCHAR(20);
```

#### 3. Periodic Version Check Endpoint

```http
GET /v1/checkFirmwareUpdate?device_id=123456
Access-Token: device_token

Response:
{
  "update_available": true,
  "latest_version": "1.1.0",
  "download_url": "https://server.com/firmware/v1.1.0.bin"
}
```

### Benefits
- **Fleet management** (know which devices are outdated)
- **Targeted OTA updates**
- **Debugging support** (correlate issues with versions)

---

## Priority 6: Error Retry Logic with Exponential Backoff

### Current State
- ❌ Failed requests are retried immediately or discarded
- ❌ Can overload server during outages
- ❌ Wastes power with repeated failed attempts

### Goal
Implement smart retry logic that backs off on repeated failures.

### Implementation

```c
#define MAX_RETRY_ATTEMPTS 5
#define BASE_RETRY_DELAY_SEC 10
#define MAX_RETRY_DELAY_SEC 300  // 5 minutes

typedef struct {
    int attempt_count;
    int next_retry_delay;
} retry_state_t;

/**
 * @brief Calculate next retry delay using exponential backoff
 */
int calculate_retry_delay(retry_state_t *state) {
    if (state->attempt_count >= MAX_RETRY_ATTEMPTS) {
        return MAX_RETRY_DELAY_SEC;
    }
    
    int delay = BASE_RETRY_DELAY_SEC * (1 << state->attempt_count);
    if (delay > MAX_RETRY_DELAY_SEC) {
        delay = MAX_RETRY_DELAY_SEC;
    }
    
    state->attempt_count++;
    state->next_retry_delay = delay;
    return delay;
}
```

**Retry Schedule:**
- Attempt 1: 10s delay
- Attempt 2: 20s delay
- Attempt 3: 40s delay
- Attempt 4: 80s delay
- Attempt 5+: 300s delay (5 min)

### Benefits
- **Reduced server load** during outages
- **Power savings** (less frequent failed attempts)
- **Automatic recovery** when connectivity restored

---

## Implementation Priority Summary

### Phase 1: Core Reliability (Week 1-2)
1. ✅ Server-side geofence breach detection
2. ✅ Notification system (email & SMS)
3. 🔧 A-GNSS integration (faster GPS fixes)
4. 🔧 Offline buffering (no data loss)

### Phase 2: Optimization (Week 3-4)
5. Adaptive upload frequency (battery savings)
6. Battery-aware transmission (extended runtime)
7. Error retry with backoff (reliability)

### Phase 3: Management (Week 5+)
8. Firmware version reporting
9. OTA update mechanism
10. Remote diagnostics

---

## Testing Checklist

For each feature:
- [ ] Unit tests for new functions
- [ ] Integration test with server
- [ ] Power consumption measurement
- [ ] Edge case testing (no network, low battery, etc.)
- [ ] Long-term stability test (24h+ runtime)

---

## Configuration Management

All new features should be configurable via Kconfig:
```
menu "GPS Tracking Features"

config ENABLE_AGNSS
    bool "Enable A-GNSS for faster GPS fixes"
    default y

config ENABLE_GPS_BUFFER
    bool "Enable offline GPS point buffering"
    default y

config ENABLE_ADAPTIVE_FREQUENCY
    bool "Enable adaptive upload frequency based on motion"
    default y

config ENABLE_BATTERY_AWARE
    bool "Enable battery-aware transmission rates"
    default y

endmenu
```

This allows features to be enabled/disabled per build.
