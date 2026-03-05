# MQTT-style realtime flow: one ingest, all clients updated

This doc describes how **any** location data streamed from the tracker (HTTP or WebSocket) is treated the same: persisted, geofenced, and broadcast to app/website so everyone sees updates straight away.

## Idea

- **Single ingest path**: One shared “ingest” step: persist GPS point, run geofence breach logic, then broadcast.
- **Two entry points**: Tracker can send location via **HTTP** (`POST /sendGPSData`) or via **WebSocket** (`location_update` message). Both go through the same ingest; no difference for the server or for clients.
- **Clients**: App and website subscribe to the device over WebSocket (`/ws/users/{device_id}`). They receive the same `location_update` messages whether the tracker sent via HTTP or WS.

So: *anything streamed by the tracker is stored and pushed to the other clients immediately* — like a single logical “device channel” with one source of truth.

## Flow

| Source | Entry | Ingest | Broadcast |
|--------|--------|--------|-----------|
| Tracker (HTTP) | `POST /sendGPSData` | `ingest_location()` → DB + geofence | `broadcast_location_update` + `broadcast_geofence_breach` |
| Tracker (WS)   | `location_update` on `/ws/devices/{id}` | `ingest_location()` → DB + geofence | same |

- **Ingest** (in `api/services/device_ingest.py`): Validates payload, writes one row to `gps_data`, runs geofence checks and email/SMS notifications, returns `(location_data, breach_events)`.
- **Broadcast**: Server sends `location_update` to room `user_device_{device_id}` (app + website) and, for each breach, `geofence_breach` to the same room.

Controls (e.g. kill switch) are separate: app/website → `PUT /v1/devices/{id}/controls` → DB → broadcast to `device_{id}` (tracker) and `user_device_{id}` (app/website). See CONTROLS_RELIABILITY.md.

## Rooms

- `device_{device_id}`: tracker WebSocket (device sends location, receives controls).
- `user_device_{device_id}`: all users (app + website) watching that device; they receive location updates and geofence alerts.

## Implementation notes

- **Device WS `location_update`**: If the message `data` contains `latitude` and `longitude`, the server runs `ingest_location(device_id, data)` (in a thread so the event loop is not blocked), then broadcasts the returned `location_data` and any breach events. If `data` is missing or invalid, the server only forwards the message to `user_device_{id}` (no persist), for backwards compatibility.
- **HTTP `sendGPSData`**: Builds a payload from the request body and calls the same `ingest_location()`; then the same broadcast logic as above.

This gives you an MQTT-like behaviour: one logical stream per device, with server as the hub that stores and fans out to all subscribers.
