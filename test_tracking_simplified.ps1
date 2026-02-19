# Test simplified tracking API (remote_viewing only)

$baseUrl = "http://localhost:8000"

# Test credentials
$email = "john.doe@example.com"
$password = "securepassword123"

Write-Host "=== Testing Simplified Tracking API ===" -ForegroundColor Cyan
Write-Host ""

# 1. Login
Write-Host "1. Logging in..." -ForegroundColor Yellow
$loginResponse = Invoke-RestMethod -Uri "$baseUrl/v1/login" -Method POST -ContentType "application/json" -Body (@{
    email_address = $email
    password = $password
} | ConvertTo-Json)

if ($loginResponse.access_token) {
    Write-Host "✓ Login successful" -ForegroundColor Green
    $token = $loginResponse.access_token
    $userId = $loginResponse.user_id
} else {
    Write-Host "✗ Login failed" -ForegroundColor Red
    exit 1
}

Write-Host ""

# 2. Get devices list
Write-Host "2. Getting devices for user $userId..." -ForegroundColor Yellow
$headers = @{
    "Access-Token" = $token
    "Accept" = "application/json"
}

$devicesResponse = Invoke-RestMethod -Uri "$baseUrl/v1/devices?user_id=$userId" -Method GET -Headers $headers

Write-Host "✓ Found $($devicesResponse.Count) device(s)" -ForegroundColor Green

if ($devicesResponse.Count -gt 0) {
    $device = $devicesResponse[0]
    Write-Host "Device ID: $($device.device_id)" -ForegroundColor Gray
    Write-Host "SMS Number: $($device.sms_number)" -ForegroundColor Gray
    Write-Host "Remote Viewing: $($device.remote_viewing)" -ForegroundColor Gray
    Write-Host "Last Viewed At: $($device.last_viewed_at)" -ForegroundColor Gray
    
    # Check that old fields are NOT present
    if ($device.PSObject.Properties.Name -contains "hot_mode") {
        Write-Host "✗ ERROR: hot_mode field still present!" -ForegroundColor Red
    } else {
        Write-Host "✓ hot_mode field removed (correct)" -ForegroundColor Green
    }
    
    if ($device.PSObject.Properties.Name -contains "hot_upload_interval_ms") {
        Write-Host "✗ ERROR: hot_upload_interval_ms field still present!" -ForegroundColor Red
    } else {
        Write-Host "✓ hot_upload_interval_ms field removed (correct)" -ForegroundColor Green
    }
    
    Write-Host ""
    
    # 3. Update tracking - set remote_viewing=true
    Write-Host "3. Setting remote_viewing=true..." -ForegroundColor Yellow
    $deviceId = $device.device_id
    
    $trackingBody = @{
        remote_viewing = $true
    } | ConvertTo-Json
    
    $updateResponse = Invoke-RestMethod -Uri "$baseUrl/v1/devices/$deviceId/tracking?user_id=$userId" -Method PUT -Headers $headers -ContentType "application/json" -Body $trackingBody
    
    Write-Host "✓ Tracking updated successfully" -ForegroundColor Green
    Write-Host "Remote Viewing: $($updateResponse.remote_viewing)" -ForegroundColor Gray
    Write-Host "Last Viewed At: $($updateResponse.last_viewed_at)" -ForegroundColor Gray
    
    # Verify update
    if ($updateResponse.remote_viewing -eq $true) {
        Write-Host "✓ remote_viewing set to true (correct)" -ForegroundColor Green
    } else {
        Write-Host "✗ ERROR: remote_viewing not updated!" -ForegroundColor Red
    }
    
    Write-Host ""
    
    # 4. Get single device
    Write-Host "4. Getting single device $deviceId..." -ForegroundColor Yellow
    $singleDeviceResponse = Invoke-RestMethod -Uri "$baseUrl/v1/devices/$deviceId?user_id=$userId" -Method GET -Headers $headers
    
    Write-Host "✓ Device retrieved" -ForegroundColor Green
    Write-Host "Remote Viewing: $($singleDeviceResponse.remote_viewing)" -ForegroundColor Gray
    Write-Host "Last Viewed At: $($singleDeviceResponse.last_viewed_at)" -ForegroundColor Gray
    
    # Verify fields are not present
    if ($singleDeviceResponse.PSObject.Properties.Name -contains "hot_mode") {
        Write-Host "✗ ERROR: hot_mode field still present in single device response!" -ForegroundColor Red
    } else {
        Write-Host "✓ hot_mode field removed from single device (correct)" -ForegroundColor Green
    }
    
    Write-Host ""
    
    # 5. Set remote_viewing=false
    Write-Host "5. Setting remote_viewing=false..." -ForegroundColor Yellow
    $trackingBody = @{
        remote_viewing = $false
    } | ConvertTo-Json
    
    $updateResponse2 = Invoke-RestMethod -Uri "$baseUrl/v1/devices/$deviceId/tracking?user_id=$userId" -Method PUT -Headers $headers -ContentType "application/json" -Body $trackingBody
    
    Write-Host "✓ Tracking updated to false" -ForegroundColor Green

    
} else {

}
Write-Host ''
Write-Host '=== Test Complete ==='
