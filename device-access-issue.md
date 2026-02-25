# Device Access Token vs User ID Issue: GPS Tracking Backend

## Summary

Device requests to `/v1/devices/{device_id}` using only the device access token are returning `{"detail":"User ID is required"}`. This prevents devices from fetching their configuration as intended.

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

## Next Steps
1. Rebuild the backend container to ensure the code change is active.
2. Double-check for any other middleware or validation enforcing `user_id`.
3. Confirm device-only requests succeed after rebuild.

---

**Last tested:** 2026-02-25

**Device access token used:** `sim_device_12345_123456789`
**Device ID:** 67
**User ID:** 2
