@echo off
REM Start GPS Tracking API, DB, and localtunnel with auto-restart (Windows)
:loop
  echo [INFO] Starting Docker containers...
  docker start gps-tracking-api gps-tracking-db
  timeout /t 3
  echo [INFO] Starting localtunnel...
  npx localtunnel --port 8000 --subdomain chatty-otter-15
  echo [WARN] localtunnel exited. Restarting in 5 seconds...
  timeout /t 5
  goto loop
