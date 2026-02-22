# Device-in-Vehicle Readiness & Production Evaluation

This document summarizes what is needed to put devices into vehicles and to run the server, app, and website in production. It also evaluates app/website alignment with the server.

---

## 1. What’s needed to put devices into vehicles

### End-to-end device flow (already implemented)

**Users add trackers via the app or website** (no commands): in the app go to **Settings → Add physical tracker** (Device ID + Pairing code); on the website open the **device dropdown → Add new tracker** (same fields). Both flows call register then link.

| Step | Action | Endpoint / behaviour | Auth |
|------|--------|----------------------|------|
| 1 | **Register device** | `POST /v1/registerDevice` – body: `device_id`, `access_token`, `sms_number`, `name?`, `control_1`–`control_4`? | None (by design for first-time provisioning) |
| 2 | **Link device to user** | `POST /v1/registerDeviceToUser` – query `user_id`, body `{ device_id }`, header `Access-Token` (user token) | User |
| 3 | **Send GPS from device** | `POST /v1/sendGPSData` – header `Access-Token` (device token), body: `device_id`, `latitude`, `longitude`, `timestamp`, `speed?`, `heading?`, `trip_active?` | Device |
| 4 | **Device polls controls** | `GET /v1/getDeviceControls?device_id=` – header `Access-Token` (device token) | Device |
| 5 | **User updates controls** | `PUT /v1/devices/{id}/controls` – user token + `user_id`; server broadcasts to device via WebSocket | User |
| 6 | **A-GNSS (assisted GPS)** | `GET /v1/agnss?device_id=&lat=&lon=` – header `Access-Token` (device token) | Device |
| 7 | **Cell-based location** | `POST /v1/cell_location` – header `Access-Token` (device token), body `{ cells[], device_id? }` | Device |
| 8 | **Device WebSocket** | `WS /v1/ws/devices/{device_id}?token=` – device token; device can send `ping`→`pong`, `location_update` | Device |
| 9 | **User real-time view** | `WS /v1/ws/users/{device_id}?token=` – user token; receives `location_update`, `device_control_response` | User |

### Gaps to close for “devices in vehicles”

1. **Documentation**
   - Single “device lifecycle” doc (this flow) linked from README.
   - README: fix “JWT-based” → **opaque access tokens**; fix `DATABASE_URL` → **`DATABASE_URI`**.

2. **Environment**
   - `.env.example`: add `DATABASE_URI` and optional `AGNSS_PROVIDER`, `AGNSS_CACHE_*`, `CELL_LOCATION_PROVIDER`, `SUPL_DEMO`.
   - Production: do not commit real keys; use secrets (e.g. ECS task env, GitHub secrets).

3. **Security**
   - **CORS**: restrict in production via `CORS_ORIGINS` (e.g. `https://yourdomain.com,https://app.yourdomain.com`). Default `*` is unsafe.
   - **Rate limiting**: consider adding for login, signup, `registerDevice`, `sendGPSData` to avoid abuse.
   - **GET /v1/ws/stats/{device_id}**: currently no auth; consider requiring user or device token or removing in production.

4. **Migrations**
   - Docker init runs `database/*.sql` and migrations. For non-Docker production, run base schema + `migration_001_add_features.sql` through `migration_004_*` in order and document in README.

5. **Device registration**
   - `registerDevice` is intentionally unauthenticated so new hardware can onboard. Mitigations: SMS number uniqueness, optional CAPTCHA or invite codes later.

---

## 2. Server production readiness

| Item | Status | Notes |
|------|--------|--------|
| Run method | ✅ | Docker Compose, ECR/ECS workflow |
| Env vars | ⚠️ | `.env.example` updated; README still says DATABASE_URL |
| Migrations | ⚠️ | SQL files for Docker; document manual run for non-Docker |
| Device flow | ✅ | Implemented; doc in this file |
| sendGPSData auth | ✅ | Device token required |
| CORS | ⚠️ | Use `CORS_ORIGINS` in production |
| Rate limiting | ❌ | Not implemented |
| ws/stats auth | ❌ | No auth |
| Secrets in compose | ⚠️ | Use env/secrets in production |

---

## 3. App (GPS-Tracking-App) vs server

- **API contract**: Aligned. App uses `Access-Token` header, `user_id` query, same paths (signup, login, devices, GPSData, controls, tracking, trip, geofences, registerDeviceToUser, sendGPSData), WebSocket `/v1/ws/users/{deviceId}?token=` with user token.
- **API base URL**: Was build-time only in `config.js`. Use **`EXPO_PUBLIC_API_URL`** for production so one build can target prod without editing code.
- **Production**: Set `EXPO_PUBLIC_API_URL` in EAS or build env; release builds should use HTTPS only (no cleartext in release). Move Google Maps API key to env/secrets and restrict by package/signing in Google Cloud.

---

## 4. Website (GPS-Tracking-Website) vs server

- **API contract**: Aligned. Website uses `Access-Token` (and Bearer), `user_id` query, same endpoints as app for login, devices, map/GPSData, controls, tracking, trip, geofences, registerDeviceToUser; WebSocket `/v1/ws/users/{deviceId}?token=`.
- **API base URL**: Was hardcoded in `GpsTrackingApi.ts`. Use **`EXPO_PUBLIC_API_URL`** (Expo web) so production build points to live API.
- **Dashboard simulator**: Uses a separate hardcoded host for registerDevice/registerDeviceToUser/sendGPSData; should use same API base as the rest of the site (or config).
- **Production**: Build with `expo export --platform web`; set `EXPO_PUBLIC_API_URL` for production. Restrict CORS on server to the website origin. Move Google Maps key to env and restrict by referrer.

---

## 5. Summary checklist

**To put devices in vehicles:**
- [x] Server implements register → link → GPS → controls → A-GNSS → cell → WebSocket.
- [x] Device flow documented (this doc).
- [x] README: DATABASE_URI and auth description fixed.
- [x] .env.example: DATABASE_URI and optional vars (AGNSS, CELL_LOCATION, CORS_ORIGINS).
- [x] CORS configurable via `CORS_ORIGINS` for production.

**App production-ready:**
- [x] API matches server.
- [x] API URL from `EXPO_PUBLIC_API_URL` (fallback in config.js).
- [ ] Production build uses HTTPS; Maps key from env/restricted.

**Website production-ready:**
- [x] API matches server.
- [x] API URL from `EXPO_PUBLIC_API_URL` (fallback in GpsTrackingApi.ts).
- [x] Simulator uses same API base (state.baseUrl / GpsTrackingApi.getBaseUrl()); Settings setBaseUrl works.
- [ ] Maps key from env/restricted.

**Server production-hardening:**
- [ ] CORS restricted to real origins.
- [ ] Optional: rate limiting, auth for GET /v1/ws/stats.
