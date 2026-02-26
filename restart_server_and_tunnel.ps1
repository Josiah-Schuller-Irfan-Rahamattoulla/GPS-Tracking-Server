# PowerShell script to auto-restart FastAPI server and loca.lt tunnel
# Run in a PowerShell terminal

while ($true) {
    Write-Host "Starting FastAPI server..."
    $server = Start-Process -FilePath "uvicorn" -ArgumentList "api.main:app --host 0.0.0.0 --port 8000" -NoNewWindow -PassThru
    Start-Sleep -Seconds 5
    Write-Host "Starting loca.lt tunnel..."
    $tunnel = Start-Process -FilePath "npx" -ArgumentList "loca.lt --port 8000 --subdomain chatty-otter-15" -NoNewWindow -PassThru

    while ($true) {
        Start-Sleep -Seconds 10
        if ($server.HasExited) {
            Write-Host "Server stopped. Restarting..."
            $server = Start-Process -FilePath "uvicorn" -ArgumentList "api.main:app --host 0.0.0.0 --port 8000" -NoNewWindow -PassThru
        }
        if ($tunnel.HasExited) {
            Write-Host "Tunnel stopped. Restarting..."
            $tunnel = Start-Process -FilePath "npx" -ArgumentList "loca.lt --port 8000 --subdomain chatty-otter-15" -NoNewWindow -PassThru
        }
    }
}
