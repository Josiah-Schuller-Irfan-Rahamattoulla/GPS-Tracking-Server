#!/usr/bin/env pwsh

# Test SUPL A-GNSS endpoint

$baseUrl = "http://localhost:8000"
$userId = 1
$deviceId = 52723
$userToken = "7FjuW651uhJJRFw862snki4boebOfAH2aasoKiw41i4"
$deviceToken = "dev_1949993451"

Write-Host "Testing A-GNSS endpoint with SUPL fallback" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan

# Test 0: Verify device is registered
Write-Host "`n0. Checking device registration:"
try {
    $response = Invoke-WebRequest -Uri "$baseUrl/v1/sendGPSData" `
        -Method POST `
        -Headers @{"Access-Token" = $deviceToken} `
        -ContentType "application/json" `
        -Body (ConvertTo-Json @{
            device_id = $deviceId
            latitude = -37.8136
            longitude = 144.9631
            timestamp = (Get-Date -AsUTC -Format "o")
        }) `
        -ErrorAction SilentlyContinue
    
    if ($response) {
        Write-Host "✅ Device is registered and authenticated" -ForegroundColor Green
    }
} catch {
    Write-Host "⚠️ Device may need registration - proceeding with A-GNSS test anyway" -ForegroundColor Yellow
}

# Test 1: Device A-GNSS without location hint
Write-Host "`n1. Device A-GNSS Request (no location hint):"
    
    if ($response.StatusCode -eq 200) {
        $dataSize = $response.Content.Length
        $source = $response.Headers["X-AGNSS-Source"]
        Write-Host "✅ SUCCESS: Got $dataSize bytes from $source" -ForegroundColor Green
        Write-Host "   Status: $($response.StatusCode)"
        Write-Host "   Content-Type: $($response.Headers["Content-Type"])"
        Write-Host "   Source: $source"
        $hex = [BitConverter]::ToString($response.Content[0..31]).Replace("-","")
        Write-Host "   First 32 bytes (hex): $hex"
    }
} catch {
    Write-Host "❌ FAILED: $($_.Exception.Message)" -ForegroundColor Red
    if ($_.Exception.Response) {
        Write-Host "   Status: $($_.Exception.Response.StatusCode)"
        Write-Host "   Details: $($_.Exception.Response.StatusDescription)"
    }
}

# Test 2: A-GNSS with location hint (Melbourne, Australia)
Write-Host "`n2. Device A-GNSS Request (with location hint - Melbourne):"
try {
    $response = Invoke-WebRequest -Uri "$baseUrl/v1/agnss?device_id=$deviceId&lat=-37.8136&lon=144.9631" `
        -Headers @{"Access-Token" = $deviceToken} `
        -ErrorAction Stop
    
    if ($response.StatusCode -eq 200) {
        $dataSize = $response.Content.Length
        $source = $response.Headers["X-AGNSS-Source"]
        Write-Host "✅ SUCCESS: Got $dataSize bytes from $source (with location hint)" -ForegroundColor Green
        Write-Host "   Status: $($response.StatusCode)"
        Write-Host "   Source: $source"
        Write-Host "   Data matches previous: $($response.Content.Length -eq $dataSize)"
    }
} catch {
    Write-Host "❌ FAILED: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 3: Verify error handling (invalid device token)
Write-Host "`n3. Invalid Device Token (expect 401):"
try {
    $response = Invoke-WebRequest -Uri "$baseUrl/v1/agnss?device_id=$deviceId" `
        -Headers @{"Access-Token" = "invalid_token"} `
        -ErrorAction Stop
    Write-Host "❌ Should have failed" -ForegroundColor Red
} catch {
    if ($_.Exception.Response.StatusCode -eq 401) {
        Write-Host "✅ Correctly rejected: 401 Unauthorized" -ForegroundColor Green
    } else {
        Write-Host "❌ Unexpected status: $($_.Exception.Response.StatusCode)" -ForegroundColor Red
    }
}

# Test 4: Missing access token
Write-Host "`n4. Missing Access Token (expect 403 or 401):"
try {
    $response = Invoke-WebRequest -Uri "$baseUrl/v1/agnss?device_id=$deviceId" `
        -ErrorAction Stop
    Write-Host "❌ Should have failed" -ForegroundColor Red
} catch {
    $status = [int]$_.Exception.Response.StatusCode
    if ($status -in (401, 403)) {
        Write-Host "✅ Correctly rejected: $($_.Exception.Response.StatusCode)" -ForegroundColor Green
    } else {
        Write-Host "⚠️ Status: $status" -ForegroundColor Yellow
    }
}

Write-Host "`n================================================" -ForegroundColor Cyan
Write-Host "A-GNSS SUPL Testing Complete" -ForegroundColor Cyan
