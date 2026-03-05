# Device controls API (kill switch, etc.)

## Update controls (user → server → device)

- **URL:** `PUT /v1/devices/{device_id}/controls`  
  **Not** `/v1/ws/devices/{id}` (that is the WebSocket path; controls are updated via REST).
- **Headers:** `Access-Token: <user token>`, `Content-Type: application/json`
- **Query:** `user_id=<user_id>` (required)
- **Body:** `{ "control_1": true/false, "control_2": true/false, ... }`

Example (PowerShell):

```powershell
$token = "YOUR_USER_ACCESS_TOKEN"
$userId = 123   # your user_id
$body = @{ control_1 = $true; control_2 = $true; control_3 = $true; control_4 = $true } | ConvertTo-Json
Invoke-RestMethod -Uri "https://gpstracking.josiahschuller.au/v1/devices/67/controls?user_id=$userId" `
  -Method Put -Headers @{ "Access-Token" = $token; "Content-Type" = "application/json" } -Body $body
```

## How the device gets the latest controls (no “only works right after connect”)

1. **While the device is connected**  
   The server broadcasts every control update to the device’s WebSocket room. The device applies them immediately (e.g. `WS control payload applied c1=1 ...`).

2. **When the device (re)connects**  
   On every connect the server sends a **welcome** message with the current controls (re-fetched from DB). So any changes you made while the device was disconnected are applied as soon as it reconnects.

3. **Result**  
   You can send controls at any time. If the device is connected, it gets them via WebSocket. If it’s disconnected, it will apply them from the welcome message on the next connect. No need to “send within a few seconds of connect”.

4. **Keeping the connection up more often**  
   - Set ALB idle timeout to 3600 s (e.g. via GitHub Actions variable `AWS_ALB_NAME`) so the WebSocket stays open longer.  
   - Firmware pings right after connect and uses a 10 s recv timeout so keepalive is frequent.
