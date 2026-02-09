# Test cell-based location endpoint
# This simulates what the nRF9151 firmware would send

$headers = @{
    "Access-Token" = "sim_device_12345_123456789"
    "Content-Type" = "application/json"
}

# Example cell tower info (UK O2 network)
# In real firmware, you'd get this from lte_lc_cell_info_get()
$body = @{
    cells = @(
        @{
            cellId = 12345
            mcc = 234        # UK
            mnc = 10         # O2
            lac = 5432
            signal = -85     # RSSI in dBm
            tac = 54321      # Optional tracking area code
        }
    )
    device_id = 67           # Use existing device
} | ConvertTo-Json

Write-Host "Testing cell location endpoint..." -ForegroundColor Cyan
Write-Host "Request body:" -ForegroundColor Yellow
Write-Host $body

try {
    $response = Invoke-WebRequest `
        -Uri "http://localhost:8000/v1/cell_location" `
        -Method POST `
        -Headers $headers `
        -Body $body `
        -UseBasicParsing
    
    Write-Host "`n✅ Response Status: $($response.StatusCode)" -ForegroundColor Green
    Write-Host "Response Body:" -ForegroundColor Yellow
    $result = $response.Content | ConvertFrom-Json
    Write-Host "  Latitude:  $($result.latitude)"
    Write-Host "  Longitude: $($result.longitude)"
    Write-Host "  Accuracy:  $($result.accuracy) meters"
    Write-Host "  Source:    $($result.source)"
} catch {
    Write-Host "`n❌ Error: $($_.Exception.Message)" -ForegroundColor Red
    if ($_.Exception.Response) {
        $reader = [System.IO.StreamReader]::new($_.Exception.Response.GetResponseStream())
        $errorBody = $reader.ReadToEnd()
        Write-Host "Error details: $errorBody" -ForegroundColor Red
    }
}
