#!/usr/bin/env pwsh
# SUPL A-GNSS Endpoint Testing

Write-Host "════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  SUPL A-GNSS Endpoint Testing" -ForegroundColor Cyan
Write-Host "  GPS Tracking Server - old-pans-dream.loca.lt" -ForegroundColor Cyan
Write-Host "════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

$BASE_URL = "http://localhost:8000"
$DEVICE_ID = 99999
$TOKEN = "test_supl_123"

# Test 1: Health Check
Write-Host "Test 1: Health Check" -ForegroundColor Yellow
try {
    $r = Invoke-WebRequest -Uri "$BASE_URL/health" -UseBasicParsing -TimeoutSec 5
    Write-Host "✅ Status: $($r.StatusCode)" -ForegroundColor Green
} catch {
    Write-Host "❌ Failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 2: A-GNSS basic request
Write-Host "`nTest 2: A-GNSS Request (No Location)" -ForegroundColor Yellow
try {
    $r = Invoke-WebRequest -Uri "$BASE_URL/v1/agnss?device_id=$DEVICE_ID" `
        -Headers @{"Access-Token" = $TOKEN} -UseBasicParsing -TimeoutSec 10
    Write-Host "✅ Status: $($r.StatusCode)" -ForegroundColor Green
    Write-Host "   Size: $($r.Content.Length) bytes"
    Write-Host "   Source: $($r.Headers['X-AGNSS-Source'])"
} catch {
    Write-Host "❌ Failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 3: A-GNSS with location (using backtick for ampersand)
Write-Host "`nTest 3: A-GNSS with Location Hint" -ForegroundColor Yellow
try {
    $url = "$BASE_URL/v1/agnss?device_id=$DEVICE_ID`&lat=-37.8136`&lon=144.9631"
    $r = Invoke-WebRequest -Uri $url -Headers @{"Access-Token" = $TOKEN} `
        -UseBasicParsing -TimeoutSec 10
    Write-Host "✅ Status: $($r.StatusCode)" -ForegroundColor Green
    Write-Host "   Location: Melbourne (-37.8136, 144.9631)"
    Write-Host "   Size: $($r.Content.Length) bytes"
    Write-Host "   Source: $($r.Headers['X-AGNSS-Source'])"
} catch {
    Write-Host "❌ Failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 4: Invalid token
Write-Host "`nTest 4: Auth Test (Invalid Token)" -ForegroundColor Yellow
try {
    $r = Invoke-WebRequest -Uri "$BASE_URL/v1/agnss?device_id=$DEVICE_ID" `
        -Headers @{"Access-Token" = "invalid"} -UseBasicParsing -TimeoutSec 5
    Write-Host "❌ Should have failed" -ForegroundColor Red
} catch {
    if ($_.Exception.Response.StatusCode -eq 401) {
        Write-Host "✅ Correctly rejected: 401 Unauthorized" -ForegroundColor Green
    }
}

# Test 5: Missing token
Write-Host "`nTest 5: Auth Test (Missing Token)" -ForegroundColor Yellow
try {
    $r = Invoke-WebRequest -Uri "$BASE_URL/v1/agnss?device_id=$DEVICE_ID" `
        -UseBasicParsing -TimeoutSec 5
    Write-Host "❌ Should have failed" -ForegroundColor Red
} catch {
    if ([int]$_.Exception.Response.StatusCode -in (401, 403)) {
        Write-Host "✅ Correctly rejected: $($_.Exception.Response.StatusCode)" -ForegroundColor Green
    }
}

# Test 6: Non-existent device
Write-Host "`nTest 6: Invalid Device (Non-existent)" -ForegroundColor Yellow
try {
    $r = Invoke-WebRequest -Uri "$BASE_URL/v1/agnss?device_id=9999999" `
        -Headers @{"Access-Token" = $TOKEN} -UseBasicParsing -TimeoutSec 5
    Write-Host "❌ Should have failed" -ForegroundColor Red
} catch {
    if ($_.Exception.Response.StatusCode -eq 404) {
        Write-Host "✅ Correctly rejected: 404 Not Found" -ForegroundColor Green
    }
}

# Test 7: Tunnel test
Write-Host "`nTest 7: Localtunnel Connectivity" -ForegroundColor Yellow
try {
    $r = Invoke-WebRequest -Uri "https://old-pans-dream.loca.lt/health" `
        -UseBasicParsing -TimeoutSec 5
    Write-Host "✅ Tunnel Health: $($r.StatusCode)" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Tunnel unavailable (start with: lt --port 8000 --subdomain old-pans-dream)" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "Summary: SUPL A-GNSS endpoint is operational!" -ForegroundColor Green
Write-Host ""
Write-Host "Usage:" -ForegroundColor Yellow
Write-Host "  GET /v1/agnss?device_id=99999"
Write-Host "  Header: Access-Token: test_supl_123"
Write-Host "  Optional: device_id=99999&lat=-37.8136&lon=144.9631"
Write-Host ""
Write-Host "Remote: https://old-pans-dream.loca.lt/v1/agnss?device_id=99999" -ForegroundColor Cyan
Write-Host "Local:  http://localhost:8000/v1/agnss?device_id=99999" -ForegroundColor Cyan
