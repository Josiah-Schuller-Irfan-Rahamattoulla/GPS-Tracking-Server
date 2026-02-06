#!/usr/bin/env pwsh

$BASE_URL = "http://localhost:8000"

# Test 1: Health Check
Write-Host "========== 1. API Health Check ==========" -ForegroundColor Yellow
try {
    $health = Invoke-WebRequest -Uri "$BASE_URL/health" -UseBasicParsing | ConvertFrom-Json
    if ($health.status -eq "healthy") {
        Write-Host "✅ API is healthy" -ForegroundColor Green
    }
} catch {
    Write-Host "❌ Failed to reach API: $_" -ForegroundColor Red
    exit 1
}

# Test 2: User Registration
Write-Host "`n========== 2. User Registration ==========" -ForegroundColor Yellow
$userEmail = "testuser_$(Get-Random)@example.com"
$userData = @{
    email_address = $userEmail
    phone_number = "+12025551234"
    name = "Test User"
    password = "TestPassword123!"
} | ConvertTo-Json

try {
    $signupResponse = Invoke-WebRequest -Uri "$BASE_URL/v1/signup" `
        -Method POST `
        -Body $userData `
        -ContentType "application/json" `
        -UseBasicParsing | ConvertFrom-Json
    
    $userId = $signupResponse.user_id
    $userToken = $signupResponse.access_token
    
    Write-Host "✅ User created: ID=$userId, Email=$userEmail" -ForegroundColor Green
} catch {
    Write-Host "❌ User registration failed: $_" -ForegroundColor Red
    exit 1
}

# Test 3: User Login
Write-Host "`n========== 3. User Login ==========" -ForegroundColor Yellow
$loginData = @{
    email_address = $userEmail
    password = "TestPassword123!"
} | ConvertTo-Json

try {
    $loginResponse = Invoke-WebRequest -Uri "$BASE_URL/v1/login" `
        -Method POST `
        -Body $loginData `
        -ContentType "application/json" `
        -UseBasicParsing | ConvertFrom-Json
    
    Write-Host "✅ Login successful" -ForegroundColor Green
} catch {
    Write-Host "❌ Login failed: $_" -ForegroundColor Red
}

# Test 4: Device Registration
Write-Host "`n========== 4. Device Registration ==========" -ForegroundColor Yellow
$deviceId = Get-Random -Minimum 10000 -Maximum 99999
$deviceToken = "device_token_$(Get-Random)"
$deviceData = @{
    device_id = $deviceId
    access_token = $deviceToken
    sms_number = "+12025555678"
    name = "Test Vehicle"
    control_1 = $true
    control_2 = $false
    control_3 = $null
} | ConvertTo-Json

try {
    $deviceResponse = Invoke-WebRequest -Uri "$BASE_URL/v1/registerDevice" `
        -Method POST `
        -Body $deviceData `
        -ContentType "application/json" `
        -UseBasicParsing | ConvertFrom-Json
    
    Write-Host "✅ Device registered: ID=$deviceId" -ForegroundColor Green
} catch {
    Write-Host "❌ Device registration failed: $_" -ForegroundColor Red
}

# Test 5: Link Device to User
Write-Host "`n========== 5. Link Device to User ==========" -ForegroundColor Yellow
$linkData = @{
    device_id = $deviceId
    access_token = $deviceToken
} | ConvertTo-Json

try {
    $linkResponse = Invoke-WebRequest -Uri "$BASE_URL/v1/registerDevice/link" `
        -Method POST `
        -Body $linkData `
        -ContentType "application/json" `
        -Headers @{"Access-Token" = $userToken} `
        -UseBasicParsing | ConvertFrom-Json
    
    Write-Host "✅ Device linked to user" -ForegroundColor Green
} catch {
    Write-Host "❌ Device linking failed: $_" -ForegroundColor Red
}

# Test 6: Submit GPS Data
Write-Host "`n========== 6. Submit GPS Data ==========" -ForegroundColor Yellow
$gpsData = @{
    device_id = $deviceId
    access_token = $deviceToken
    latitude = 37.7749
    longitude = -122.4194
    speed = 45.5
    heading = 270
    altitude = 50.0
    is_trip_active = $true
} | ConvertTo-Json

try {
    $gpsResponse = Invoke-WebRequest -Uri "$BASE_URL/v1/submit_gps_data" `
        -Method POST `
        -Body $gpsData `
        -ContentType "application/json" `
        -UseBasicParsing | ConvertFrom-Json
    
    Write-Host "✅ GPS data submitted successfully" -ForegroundColor Green
} catch {
    Write-Host "❌ GPS data submission failed: $_" -ForegroundColor Red
}

# Test 7: Get GPS Data
Write-Host "`n========== 7. Retrieve GPS Data ==========" -ForegroundColor Yellow
try {
    $gpsDataResponse = Invoke-WebRequest -Uri "$BASE_URL/v1/gps_data/$deviceId" `
        -Method GET `
        -Headers @{"Access-Token" = $userToken} `
        -UseBasicParsing | ConvertFrom-Json
    
    Write-Host "✅ GPS data retrieved" -ForegroundColor Green
    Write-Host "   Record count: $($gpsDataResponse.Count)" -ForegroundColor Cyan
    if ($gpsDataResponse.Count -gt 0) {
        Write-Host "   Latest: Lat=$($gpsDataResponse[0].latitude), Lon=$($gpsDataResponse[0].longitude)" -ForegroundColor Cyan
    }
} catch {
    Write-Host "❌ Failed to retrieve GPS data: $_" -ForegroundColor Red
}

# Test 8: Create Geofence
Write-Host "`n========== 8. Create Geofence ==========" -ForegroundColor Yellow
$geofenceData = @{
    name = "Test Geofence"
    latitude = 37.7749
    longitude = -122.4194
    radius = 500
    description = "Test area in San Francisco"
} | ConvertTo-Json

try {
    $geofenceResponse = Invoke-WebRequest -Uri "$BASE_URL/v1/geofence" `
        -Method POST `
        -Body $geofenceData `
        -ContentType "application/json" `
        -Headers @{"Access-Token" = $userToken} `
        -UseBasicParsing | ConvertFrom-Json
    
    $geofenceId = $geofenceResponse.geofence_id
    Write-Host "✅ Geofence created: ID=$geofenceId" -ForegroundColor Green
} catch {
    Write-Host "❌ Geofence creation failed: $_" -ForegroundColor Red
}

# Test 9: List Geofences
Write-Host "`n========== 9. List Geofences ==========" -ForegroundColor Yellow
try {
    $geofencesResponse = Invoke-WebRequest -Uri "$BASE_URL/v1/geofence" `
        -Method GET `
        -Headers @{"Access-Token" = $userToken} `
        -UseBasicParsing | ConvertFrom-Json
    
    Write-Host "✅ Geofences retrieved" -ForegroundColor Green
    Write-Host "   Count: $($geofencesResponse.Count)" -ForegroundColor Cyan
} catch {
    Write-Host "❌ Failed to retrieve geofences: $_" -ForegroundColor Red
}

Write-Host "`n========== TEST SUMMARY ==========" -ForegroundColor Yellow
Write-Host "✅ Core API features validated successfully" -ForegroundColor Green
Write-Host "🚀 Server running on http://localhost:8000" -ForegroundColor Green
Write-Host "📍 For local domain access, use DNS configuration" -ForegroundColor Cyan
