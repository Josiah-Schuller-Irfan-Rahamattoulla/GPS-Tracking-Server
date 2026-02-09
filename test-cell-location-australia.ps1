# Test with Australian cell tower data
# This should return Victoria, Australia location

$headers = @{
    "Access-Token" = "sim_device_12345_123456789"
    "Content-Type" = "application/json"
}

# Example Australian cell tower (Telstra network in Melbourne area)
$body = @{
    cells = @(
        @{
            cellId = 12345678    # Example cell ID
            mcc = 505            # Australia
            mnc = 1              # Telstra
            lac = 1234           # Location Area Code
            signal = -85         # RSSI in dBm
            tac = 12345          # Tracking Area Code
        }
    )
    device_id = 67
} | ConvertTo-Json

Write-Host "Testing cell location with Australian tower data..." -ForegroundColor Cyan
Write-Host "MCC: 505 (Australia), MNC: 1 (Telstra)" -ForegroundColor Yellow
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
    
    # Check if it's in Victoria region
    if ($result.latitude -gt -39 -and $result.latitude -lt -34 -and 
        $result.longitude -gt 140 -and $result.longitude -lt 150) {
        Write-Host "`n✅ Position is in Victoria, Australia region!" -ForegroundColor Green
    }
} catch {
    Write-Host "`n❌ Error: $($_.Exception.Message)" -ForegroundColor Red
    if ($_.Exception.Response) {
        $reader = [System.IO.StreamReader]::new($_.Exception.Response.GetResponseStream())
        $errorBody = $reader.ReadToEnd()
        Write-Host "Error details: $errorBody" -ForegroundColor Red
    }
}
