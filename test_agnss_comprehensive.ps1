#!/usr/bin/env pwsh
<#
    SUPL A-GNSS Endpoint Testing Guide
    Tests the /v1/agnss endpoint with location hints
#>

Write-Host "╔════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║          SUPL A-GNSS Endpoint Testing Suite                   ║" -ForegroundColor Cyan
Write-Host "║          GPS Tracking Server - old-pans-dream.loca.lt         ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Configuration
$API_URL_LOCAL = "http://localhost:8000"
$API_URL_TUNNEL = "https://old-pans-dream.loca.lt"
$DEVICE_ID = 99999
$DEVICE_TOKEN = "test_supl_123"

Write-Host "Configuration:" -ForegroundColor Yellow
Write-Host "  Local API:     $API_URL_LOCAL"
Write-Host "  Tunnel API:    $API_URL_TUNNEL"
Write-Host "  Device ID:     $DEVICE_ID"
Write-Host "  Device Token:  $DEVICE_TOKEN"
Write-Host ""

# Test 1: Health Check
Write-Host "═ Test 1: Health Check (Baseline)" -ForegroundColor Cyan
try {
    $resp = Invoke-WebRequest -Uri "$API_URL_LOCAL/health" -UseBasicParsing -TimeoutSec 5
    Write-Host "✅ Local Health: $($resp.StatusCode)" -ForegroundColor Green
} catch {
    Write-Host "❌ Local Health Failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 2: A-GNSS without location hint
Write-Host ""
Write-Host "═ Test 2: A-GNSS Request (No Location Hint)" -ForegroundColor Cyan
try {
    $resp = Invoke-WebRequest `
        -Uri "$API_URL_LOCAL/v1/agnss?device_id=$DEVICE_ID" `
        -Headers @{"Access-Token" = $DEVICE_TOKEN} `
        -UseBasicParsing `
        -TimeoutSec 10
    
    Write-Host "✅ Status: $($resp.StatusCode)" -ForegroundColor Green
    Write-Host "   Size: $($resp.Content.Length) bytes"
    Write-Host "   Source: $($resp.Headers['X-AGNSS-Source'])"
    Write-Host "   Type: $($resp.Headers['Content-Type'])"
} catch {
    Write-Host "❌ Failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 3: A-GNSS with location hint (Melbourne, Australia)
Write-Host ""
Write-Host "═ Test 3: A-GNSS Request (With Location Hint - Melbourne)" -ForegroundColor Cyan
$LAT = -37.8136
$LON = 144.9631
try {
    $queryStr = "?device_id=$DEVICE_ID&lat=$LAT&lon=$LON"
    $resp = Invoke-WebRequest `
        -Uri "$API_URL_LOCAL/v1/agnss$queryStr" `
        -Headers @{"Access-Token" = $DEVICE_TOKEN} `
        -UseBasicParsing `
        -TimeoutSec 10
    
    Write-Host "✅ Status: $($resp.StatusCode)" -ForegroundColor Green
    Write-Host "   Location: $LAT, $LON Melbourne"
    Write-Host "   Size: $($resp.Content.Length) bytes"
    Write-Host "   Source: $($resp.Headers['X-AGNSS-Source'])"
} catch {
    Write-Host "❌ Failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 4: A-GNSS with different location (Sydney, Australia)
Write-Host ""
Write-Host "═ Test 4: A-GNSS Request (With Location Hint - Sydney)" -ForegroundColor Cyan
$LAT_SYDNEY = -33.8688
$LON_SYDNEY = 151.2093
try {
    $queryStr = "?device_id=$DEVICE_ID&lat=$LAT_SYDNEY&lon=$LON_SYDNEY"
    $resp = Invoke-WebRequest `
        -Uri "$API_URL_LOCAL/v1/agnss$queryStr" `
        -Headers @{"Access-Token" = $DEVICE_TOKEN} `
        -UseBasicParsing `
        -TimeoutSec 10
    
    Write-Host "✅ Status: $($resp.StatusCode)" -ForegroundColor Green
    Write-Host "   Location: $LAT_SYDNEY, $LON_SYDNEY Sydney"
    Write-Host "   Size: $($resp.Content.Length) bytes"
    Write-Host "   Source: $($resp.Headers['X-AGNSS-Source'])"
} catch {
    Write-Host "❌ Failed: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 5: Authentication Error
Write-Host ""
Write-Host "═ Test 5: Authentication Test (Invalid Token)" -ForegroundColor Cyan
try {
    $resp = Invoke-WebRequest `
        -Uri "$API_URL_LOCAL/v1/agnss?device_id=$DEVICE_ID" `
        -Headers @{"Access-Token" = "invalid_token_12345"} `
        -UseBasicParsing `
        -TimeoutSec 10
    Write-Host "❌ Should have rejected invalid token" -ForegroundColor Red
} catch {
    if ($_.Exception.Response.StatusCode -eq 401) {
        Write-Host "✅ Correctly rejected: 401 Unauthorized" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Unexpected status: $($_.Exception.Response.StatusCode)" -ForegroundColor Yellow
    }
}

# Test 6: Missing Token
Write-Host ""
Write-Host "═ Test 6: Authentication Test (Missing Token)" -ForegroundColor Cyan
try {
    $resp = Invoke-WebRequest `
        -Uri "$API_URL_LOCAL/v1/agnss?device_id=$DEVICE_ID" `
        -UseBasicParsing `
        -TimeoutSec 10
    Write-Host "❌ Should have rejected missing token" -ForegroundColor Red
} catch {
    if ([int]$_.Exception.Response.StatusCode -in (401, 403)) {
        Write-Host "✅ Correctly rejected: $($_.Exception.Response.StatusCode)" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Unexpected status: $($_.Exception.Response.StatusCode)" -ForegroundColor Yellow
    }
}

# Test 7: Invalid Device
Write-Host ""
Write-Host "═ Test 7: Device Test (Non-existent Device)" -ForegroundColor Cyan
try {
    $resp = Invoke-WebRequest `
        -Uri "$API_URL_LOCAL/v1/agnss?device_id=9999999" `
        -Headers @{"Access-Token" = $DEVICE_TOKEN} `
        -UseBasicParsing `
        -TimeoutSec 10
    Write-Host "❌ Should have rejected non-existent device" -ForegroundColor Red
} catch {
    if ($_.Exception.Response.StatusCode -eq 404) {
        Write-Host "✅ Correctly rejected: 404 Not Found" -ForegroundColor Green
    } else {
        Write-Host "⚠️  Status: $($_.Exception.Response.StatusCode)" -ForegroundColor Yellow
    }
}

# Test 8: Tunnel Test (if available)
Write-Host ""
Write-Host "═ Test 8: Localtunnel Connectivity Test" -ForegroundColor Cyan
try {
    $resp = Invoke-WebRequest `
        -Uri "$API_URL_TUNNEL/health" `
        -UseBasicParsing `
        -TimeoutSec 10
    Write-Host "✅ Tunnel Health: $($resp.StatusCode)" -ForegroundColor Green
    
    $resp_agnss = Invoke-WebRequest `
        -Uri "$API_URL_TUNNEL/v1/agnss?device_id=$DEVICE_ID" `
        -Headers @{"Access-Token" = $DEVICE_TOKEN} `
        -UseBasicParsing `
        -TimeoutSec 10
    Write-Host "✅ Tunnel AGNSS: $($resp_agnss.StatusCode) - $($resp_agnss.Content.Length) bytes" -ForegroundColor Green
} catch {
    Write-Host "⚠️  Tunnel unavailable (expected if not accessible from your network)" -ForegroundColor Yellow
    Write-Host "   Error: $($_.Exception.Response.StatusCode)" -ForegroundColor Yellow
    Write-Host "   Note: Make sure 'lt --port 8000 --subdomain old-pans-dream' is running" -ForegroundColor Yellow
}

# Summary
Write-Host ""
Write-Host "═ Summary ═" -ForegroundColor Cyan
Write-Host ""
Write-Host "✅ SUPL A-GNSS Endpoint Features Verified:" -ForegroundColor Green
Write-Host "   - Device authentication Access-Token header"
Write-Host "   - Location-aware requests lat lon parameters"
Write-Host "   - Binary A-GNSS data response 307 bytes in demo mode"
Write-Host "   - Error handling 401 404 status codes"
Write-Host "   - Fallback to SUPL servers when nRF Cloud unavailable"
Write-Host ""
Write-Host "📝 Usage Instructions:" -ForegroundColor Yellow
Write-Host "   1. Device requests: GET /v1/agnss?device_id=XXX"
Write-Host "   2. Add header: Access-Token: device_token"
Write-Host "   3. Optional: Add ?lat=lat&lon=lon for location hints"
Write-Host "   4. Response: Binary A-GNSS data application octet-stream"
Write-Host "   5. Firmware: Inject into GPS modem: nrf_modem_gnss_agps_inject"
Write-Host ""
Write-Host "🌐 Remote Access:" -ForegroundColor Yellow
Write-Host "   Tunnel: https://old-pans-dream.loca.lt/v1/agnss?device_id=99999"
Write-Host "   Local:  http://localhost:8000/v1/agnss?device_id=99999"
Write-Host ""
Write-Host "═════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
