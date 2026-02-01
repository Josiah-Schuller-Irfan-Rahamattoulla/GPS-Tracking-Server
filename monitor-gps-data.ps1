# GPS Data Monitor - Watch incoming data from devices
# Run: .\monitor-gps-data.ps1
# Ctrl+C to stop

$interval = 2
Write-Host "=== GPS Data Monitor (refreshing every ${interval}s, Ctrl+C to stop) ===" -ForegroundColor Cyan
Write-Host ""

while ($true) {
    Clear-Host
    Write-Host "=== GPS Data Monitor - $(Get-Date -Format 'HH:mm:ss') ===" -ForegroundColor Cyan
    Write-Host ""
    
    docker exec gps-tracking-db psql -U gpsuser -d gps_tracking -c "SELECT device_id, time AT TIME ZONE 'UTC' as time_utc, round(latitude::numeric, 6) as lat, round(longitude::numeric, 6) as lon, speed, heading, trip_active FROM gps_data ORDER BY time DESC LIMIT 10;"
    
    Write-Host ""
    Write-Host "Next refresh in ${interval}s..." -ForegroundColor DarkGray
    Start-Sleep -Seconds $interval
}
