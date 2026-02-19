# Test script for remote_viewing feature
Write-Host "`n========== REMOTE_VIEWING BACKEND TEST ==========" -ForegroundColor Cyan

# Test credentials
$userToken = "7FjuW651uhJJRFw862snki4boebOfAH2aasoKiw41i4"
$userId = 1
$deviceId = 52723

Write-Host "`n[TEST 1] Check database has remote_viewing columns" -ForegroundColor Yellow
$dbCheck = docker exec gps-tracking-db psql -U gpsuser -d gps_tracking -t -c "SELECT column_name FROM information_schema.columns WHERE table_name='devices' AND column_name IN ('remote_viewing', 'last_viewed_at');"
Write-Host $dbCheck

Write-Host "`n[TEST 2] GET /v1/devices/$deviceId - Verify endpoint returns remote_viewing" -ForegroundColor Yellow
try {
    $headers = @{ "Access-Token" = $userToken }
    $device = Invoke-RestMethod -Uri "http://localhost:8000/v1/devices/$deviceId`?user_id=$userId" -Method GET -Headers $headers
    
    Write-Host "  device_id: $($device.device_id)" -ForegroundColor Green
    Write-Host "  hot_mode: $($device.hot_mode)" -ForegroundColor Green
    Write-Host "  remote_viewing: $($device.remote_viewing)" -ForegroundColor Green
    Write-Host "  last_viewed_at: $($device.last_viewed_at)" -ForegroundColor Green
    
    if ($null -ne $device.PSObject.Properties['remote_viewing']) {
        Write-Host "  ✅ remote_viewing field present in response" -ForegroundColor Green
    } else {
        Write-Host "  ❌ remote_viewing field MISSING from response" -ForegroundColor Red
    }
} catch {
    Write-Host "  ❌ ERROR: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n[TEST 3] PUT /v1/devices/$deviceId/tracking - Update remote_viewing to true" -ForegroundColor Yellow
try {
    $headers = @{ 
        "Access-Token" = $userToken
        "Content-Type" = "application/json"
    }
    $body = '{"remote_viewing":true}'
    
    $updated = Invoke-RestMethod -Uri "http://localhost:8000/v1/devices/$deviceId/tracking?user_id=$userId" -Method PUT -Headers $headers -Body $body
    
    Write-Host "  ✅ PUT request successful" -ForegroundColor Green
    Write-Host "  remote_viewing: $($updated.remote_viewing)" -ForegroundColor Green
    Write-Host "  last_viewed_at: $($updated.last_viewed_at)" -ForegroundColor Green
} catch {
    Write-Host "  ❌ ERROR: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n[TEST 4] Verify database updated" -ForegroundColor Yellow
$dbResult = docker exec gps-tracking-db psql -U gpsuser -d gps_tracking -t -c "SELECT remote_viewing, last_viewed_at FROM devices WHERE device_id = $deviceId;"
Write-Host $dbResult

Write-Host "`n[TEST 5] PUT /v1/devices/$deviceId/tracking - Update remote_viewing to false" -ForegroundColor Yellow
try {
    $headers = @{ 
        "Access-Token" = $userToken
        "Content-Type" = "application/json"
    }
    $body = '{"remote_viewing":false}'
    
    $updated = Invoke-RestMethod -Uri "http://localhost:8000/v1/devices/$deviceId/tracking?user_id=$userId" -Method PUT -Headers $headers -Body $body
    
    Write-Host "  ✅ PUT request successful" -ForegroundColor Green
    Write-Host "  remote_viewing: $($updated.remote_viewing)" -ForegroundColor Green
} catch {
    Write-Host "  ❌ ERROR: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n[TEST 6] Verify final state" -ForegroundColor Yellow
$finalState = docker exec gps-tracking-db psql -U gpsuser -d gps_tracking -t -c "SELECT remote_viewing FROM devices WHERE device_id = $deviceId;"
Write-Host "  remote_viewing: $finalState"

Write-Host "`n========== TEST COMPLETE ==========" -ForegroundColor Cyan
