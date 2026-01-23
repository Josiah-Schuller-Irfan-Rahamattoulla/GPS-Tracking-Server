# Device Control Implementation - What's Missing

## Overview
To enable actuating low-side outputs (DRV8803 motor drivers) over the server, the following components need to be implemented:

## Current Status

### ✅ What Exists

1. **Server Side:**
   - Database fields: `control_1`, `control_2`, `control_3`, `control_4` in `devices` table
   - User endpoint: `PUT /v1/devices/{device_id}/controls` (updates controls via user token)
   - User endpoint: `GET /v1/devices/{device_id}` (gets device with controls via user token)
   - Device authentication: `authorise_device()` function exists

2. **Website/App Side:**
   - API method: `updateDeviceControls()` exists in `GpsTrackingApi.ts`
   - UI components can call the API to set controls

3. **Firmware Side:**
   - DRV8803 driver exists (`ddrv8803.h/c`)
   - GPIO pins configured for motor drivers
   - Modem library initialized for cellular communication

### ❌ What's Missing

## 1. Server: Device-Authenticated Control Endpoint

**Problem:** Devices authenticate with their own `access_token`, but there's no endpoint for devices to GET their control settings.

**Solution:** Add a new endpoint that devices can call to get their control settings.

**File:** `api/endpoints/device_data_endpoints.py`

```python
@router.get("/getDeviceControls")
async def get_device_controls(
    device_id: int,
    access_token: str = Security(access_token_header)
):
    """
    Endpoint for devices to get their control settings.
    Authenticated using device access token.
    """
    db_conn = connect(dsn=os.getenv("DATABASE_URI"))
    
    # Verify device and token
    device = get_device(db_conn=db_conn, device_id=device_id)
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Device not found"
        )
    
    if device.access_token != access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid access token"
        )
    
    return {
        "device_id": device.device_id,
        "control_1": device.control_1,
        "control_2": device.control_2,
        "control_3": device.control_3,
        "control_4": device.control_4,
        "control_version": device.control_version,  # For change detection
        "controls_updated_at": device.controls_updated_at
    }
```

**Note:** Need to import `Security` and `access_token_header` from `authorisation.py`

## 2. Firmware: Poll Server for Control Settings

**Problem:** Firmware doesn't poll the server for control commands.

**Solution:** Add periodic polling in main loop to fetch control settings.

**File:** `nrf9151-firmware/src/main.c`

**Add:**
1. Include DRV8803 driver
2. Initialize DRV8803 driver
3. Add polling logic to fetch controls from server
4. Apply control settings to motor drivers

**Implementation:**

```c
// Add to includes
#include "drivers/ddrv8803.h"

// Add to global state
static ddrv8803_dev_t motor_drivers;
static bool motor_drivers_ok = false;
static int64_t last_control_poll = 0;
#define CONTROL_POLL_INTERVAL_MS 5000  // Poll every 5 seconds

// Add to initialization (in main())
uint8_t enable_pins[4] = {
    PIN_DRV_1_ENABLED,
    PIN_DRV_2_ENABLED,
    PIN_DRV_3_ENABLED,
    PIN_DRV_4_ENABLED
};
if (ddrv8803_init(&motor_drivers, gpio_dev, enable_pins, PIN_DRV_FAULT) == 0) {
    motor_drivers_ok = true;
    LOG_INF("Motor drivers initialized");
}

// Add to main loop (after GPS transmission logic)
// Poll for control settings
if (cellular_ok && (now - last_control_poll >= CONTROL_POLL_INTERVAL_MS)) {
    last_control_poll = now;
    
    // TODO: Implement HTTP GET to /v1/getDeviceControls
    // Parse response and update motor drivers
    // modem_get_device_controls() - needs to be implemented
}
```

## 3. Firmware: HTTP GET Implementation

**Problem:** `modem_send_gps_data()` only does POST. Need GET for fetching controls.

**Solution:** Add HTTP GET function to modem driver.

**File:** `nrf9151-firmware/src/drivers/modem.c` and `modem.h`

**Add to modem.h:**
```c
/**
 * @brief Get device control settings from server
 * 
 * @param server_url Server URL
 * @param device_id Device ID
 * @param access_token Device access token
 * @param controls Output structure to store control settings
 * @return 0 on success, negative error code on failure
 */
int modem_get_device_controls(
    const char *server_url,
    uint32_t device_id,
    const char *access_token,
    bool *control_1,
    bool *control_2,
    bool *control_3,
    bool *control_4,
    uint32_t *control_version
);
```

**Implementation in modem.c:**
- Similar to `modem_send_gps_data()` but:
  - Use GET instead of POST
  - Parse JSON response instead of sending
  - Extract control_1, control_2, control_3, control_4, control_version

## 4. Firmware: Apply Control Settings to Motor Drivers

**Problem:** Even if controls are fetched, they're not applied to hardware.

**Solution:** Update motor driver states based on control settings.

**File:** `nrf9151-firmware/src/main.c`

**Add to main loop:**
```c
// After fetching controls from server
if (motor_drivers_ok) {
    // Apply control_1 to driver 0, control_2 to driver 1, etc.
    if (control_1 != NULL) {
        if (*control_1) {
            ddrv8803_enable_driver(&motor_drivers, 0);
        } else {
            ddrv8803_disable_driver(&motor_drivers, 0);
        }
    }
    // Repeat for control_2, control_3, control_4
}
```

## 5. Website/App: UI for Control Toggles

**Status:** API exists, but need to verify UI components exist.

**Check:**
- Dashboard should have toggle switches for each control
- Should call `updateDeviceControls()` when toggled
- Should show current state

**Files to check:**
- `GPS-Tracking-Website/src/components/Dashboard.tsx`
- `GPS-Tracking-App/MainScreen.js`

## Implementation Priority

1. **High Priority:**
   - Server: Add `GET /v1/getDeviceControls` endpoint (device-authenticated)
   - Firmware: Add HTTP GET function to modem driver
   - Firmware: Add polling logic in main loop

2. **Medium Priority:**
   - Firmware: Initialize DRV8803 driver
   - Firmware: Apply control settings to motor drivers

3. **Low Priority:**
   - Website/App: Verify UI exists and works
   - Add error handling and retry logic
   - Add logging for control changes

## Testing Checklist

- [ ] Server endpoint returns correct control values
- [ ] Device can authenticate and fetch controls
- [ ] Firmware polls server successfully
- [ ] Motor drivers respond to control changes
- [ ] Website/app can update controls
- [ ] Changes propagate to device within polling interval
- [ ] Error handling works (network failures, etc.)

## Notes

- Control version can be used to detect changes without polling frequently
- Consider using control_version to only poll when version changes
- Motor drivers should be initialized early in boot sequence
- Consider adding fault detection and logging


















