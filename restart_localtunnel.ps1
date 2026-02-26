# PowerShell script to auto-restart localtunnel
# Requires localtunnel installed globally: npm install -g localtunnel

while ($true) {
    Write-Host "Starting localtunnel..."
    $tunnel = Start-Process -FilePath "cmd.exe" -ArgumentList "/c lt --port 8000 --subdomain chatty-otter-15" -NoNewWindow -PassThru
    while ($true) {
        Start-Sleep -Seconds 10
        if ($tunnel.HasExited) {
            Write-Host "Tunnel stopped. Restarting..."
            $tunnel = Start-Process -FilePath "cmd.exe" -ArgumentList "/c lt --port 8000 --subdomain chatty-otter-15" -NoNewWindow -PassThru
        }
    }
}
