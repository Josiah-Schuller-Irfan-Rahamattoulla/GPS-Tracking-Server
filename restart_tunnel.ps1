# PowerShell script to auto-restart loca.lt tunnel
# Run in a PowerShell terminal

while ($true) {
    Write-Host "Starting loca.lt tunnel..."
    $tunnel = Start-Process -FilePath "cmd.exe" -ArgumentList "/c npx loca.lt --port 8000 --subdomain chatty-otter-15" -NoNewWindow -PassThru
    while ($true) {
        Start-Sleep -Seconds 10
        if ($tunnel.HasExited) {
            Write-Host "Tunnel stopped. Restarting..."
            $tunnel = Start-Process -FilePath "cmd.exe" -ArgumentList "/c npx loca.lt --port 8000 --subdomain chatty-otter-15" -NoNewWindow -PassThru
        }
    }
}
