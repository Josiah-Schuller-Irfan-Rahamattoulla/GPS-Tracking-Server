# Control reliability: send and apply at any time

This doc describes how we ensure device controls (e.g. kill switch) can be **sent and applied at any time** and stay reliable.

## Guarantees

| What | How it's ensured |
|------|------------------|
| **User can always send** | `PUT /v1/devices/{id}/controls` always accepts the request, updates the DB, and broadcasts to the device's WebSocket room. No dependency on device being online. |
| **Applied when device is connected** | Server broadcasts every control update to the device's WS room. Device applies each `device_control_response` immediately. |
| **Applied when device was disconnected** | On **every** WebSocket connect, the server sends a **welcome** message with the **current** controls (re-fetched from DB). So any change made while the device was offline is applied as soon as it reconnects. |
| **No stale state** | Welcome message is built from a fresh DB read at connect time, not from a cached device object. |

So: **send at any time** (API + DB); **apply at any time** = immediately if connected, or on next connect via welcome.

## What you must have in place

### 1. Server (already implemented)

- **Welcome on connect**  
  In `realtime_endpoints.py`, when a device connects to `/ws/devices/{id}`:
  - Re-fetch the device from the DB.
  - Send one `device_control_response` with current `control_1`..`control_4` (and related fields). Any control not set in DB is sent as `false` so the device always gets a full state.
- **Broadcast on PUT**  
  When an app user calls `PUT /v1/devices/{id}/controls`, the server updates the DB and calls `broadcast_device_control_response`: it sends to the **device** room first, then to the user room. Optionally set `CONTROL_DUPLICATE_SEND_MS=150` so the server sends the same control message to the device again after 150 ms (helps on flaky networks).

### 2. Load balancer (you configure once)

- **ALB idle timeout = 3600 s**  
  If the ALB idle timeout is 60 s (default), the WebSocket is closed after 60 s of no traffic and the device has to reconnect. That makes "apply immediately" only work in a short window after each connect.
- **Set it to 3600 s (1 hour)** so the connection stays up much longer. Then the device is usually connected when you send controls, so it gets the broadcast right away.
- **How:** In GitHub, add repo variable `AWS_ALB_NAME` (your ALB name). The `build-deploy.yml` workflow will set the idle timeout to 3600 when you deploy. Or set it manually in AWS: EC2 → Load balancers → your ALB → Attributes → Idle timeout = 3600.

### 3. Firmware (already implemented)

- **Ping after connect**  
  Right after the WebSocket connects, the device sends one `{"type":"ping"}` so the server/ALB see traffic and the first recv often gets the welcome or pong.
- **10 s recv timeout**  
  When idle, the device sends a ping every 10 s (on recv timeout), so the connection stays alive well under a 60 s (or 3600 s) idle timeout.
- **Apply every `device_control_response`**  
  Welcome and broadcasts are both `device_control_response`; the device parses `control_1`..`control_4` (true/false) and calls `apply_server_controls`.

## End-to-end flow

1. **User sends control (e.g. kill on)**  
   → `PUT /v1/devices/67/controls` with user token and body `{ "control_1": true, ... }`.  
   → Server updates DB and broadcasts to room `device_67`.

2. **If device is connected**  
   → It receives the broadcast and logs e.g. `WS control payload applied c1=1 ...`.  
   → Kill is applied immediately.

3. **If device is disconnected**  
   → Broadcast is sent but no one is in the room.  
   → When the device later connects, the server sends the **welcome** (current state from DB).  
   → Device receives welcome and applies the same controls.  
   → Kill is applied on connect.

4. **If ALB timeout is 3600 s**  
   → Device stays connected much longer, so step 2 applies most of the time and you get immediate actuation.

## Server-side reliability (implemented)

- **Device first:** On every control update (PUT), the server broadcasts to the **device** room first, then to the user room, so the tracker gets the message with priority.
- **Full state on welcome:** The welcome message always includes all four controls (`control_1`..`control_4`); any missing key is sent as `false` so the device never merges with stale state.
- **Optional duplicate send:** Set `CONTROL_DUPLICATE_SEND_MS=150` (or similar) in the server environment to send the same control message to the device **twice** (second copy after that many milliseconds). This improves delivery on flaky or lossy links; use 0 or leave unset to disable.

## Stability checklist

Use this to get **reliable and stable** control activation from app/website to tracker:

| Check | Why it matters |
|-------|----------------|
| **ALB idle timeout = 3600 s** | Default 60 s closes the WebSocket quickly; the device then only gets controls on reconnect (welcome). With 3600 s the device stays connected and receives broadcasts immediately. |
| **Device sends ping after connect** | Ensures the first server message (welcome) is delivered and the connection is seen as active by the ALB. |
| **Device uses ~10 s recv timeout and sends ping on timeout** | Keeps the connection alive so it isn’t closed by the ALB during idle periods. |
| **Firmware applies every `device_control_response`** | Both welcome and broadcast use this type; the device must parse `control_1`..`control_4` (true/false) and call `apply_server_controls`. |
| **`CONTROL_DUPLICATE_SEND_MS=150` (optional)** | On unstable networks, a second copy of each control update to the device increases the chance that at least one arrives. |

## Summary

- **Sent at any time:** API always accepts and stores; broadcast is best-effort to connected devices.
- **Applied at any time:** When connected, apply from broadcast; when not connected, apply from welcome on next connect.
- **Reliability:** Re-fetched welcome on connect + device-first broadcast + optional duplicate send + long ALB idle timeout + device keepalive (ping / 10 s recv) give you consistent, up-to-date controls with no extra HTTP poll before connect.
