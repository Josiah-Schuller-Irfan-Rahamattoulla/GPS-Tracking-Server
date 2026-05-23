# Device Access Token vs User ID Issue: GPS Tracking Backend

## Device requests to `/v1/devices/{device_id}` using only the device access token are returning `{"detail":"User ID is required"}`. This prevents devices from fetching their configuration as intended.

## Observed Behavior
- **Device request:**
  - `GET /v1/devices/67` with header `Access-Token: sim_device_12345_123456789`
  - **Response:** `400 Bad Request` with `{"detail":"User ID is required"}`
- **Device request with user_id:**
  - `GET /v1/devices/67?user_id=2` with header `Access-Token: sim_device_12345_123456789`
  - **Response:** `401 Unauthorized` with `{"detail":"Invalid access token"}`

## Expected Behavior
- Device should be able to fetch its config using only its device access token, with no `user_id` required in the query.
- User (web/app) requests should use a user access token and `user_id`.

## Root Cause
- The backend endpoint `/v1/devices/{device_id}` currently requires a `user_id` for all requests, even when a valid device access token is supplied.
- When `user_id` is present, the backend expects a user access token, not a device access token.

## Fix Attempted
- The endpoint logic was patched to:
  - Allow device-only access with a valid device access token (no `user_id` required).
  - Allow user access with a valid user access token and `user_id`.
- After patching and restarting the container, the issue persisted, suggesting the code change did not take effect or another layer is enforcing the requirement.

## App (fixed 2026-05-23)

- Mobile app poll now uses `GET /v1/devices/{device_id}?user_id=` instead of downloading the full `GET /v1/devices` list every ~15s.
- User requests: **user** `Access-Token` + `user_id` query (as implemented in `get_device_endpoint`).
- Device firmware should use `GET /v1/getDeviceControls?device_id=` with the **device** token, not `/v1/devices/{id}`.

## Firmware: settled state ignores controls (2026-05-23)

**Cause:** WS stays up (pongs only), HTTP `getDeviceControls` poll disabled while `device_ws_connected`.

**Fix:** Reflash firmware with `CONTROL_SETTLED_STATE_FIX.md` changes (HTTP fallback every 90s with coordinated WS pause; pongs no longer keep zombie WS alive).

---

## Next Steps (device token on `/devices/{id}`)

1. Optional: add `GET /v1/deviceConfig?device_id=` for firmware if not already routed.
2. Rebuild production if an older image still returns 400 without `user_id` for user app calls.

---

**Last tested:** 2026-02-25

**Device access token used:** `sim_device_12345_123456789`
**Device ID:** 67
**User ID:** 2
