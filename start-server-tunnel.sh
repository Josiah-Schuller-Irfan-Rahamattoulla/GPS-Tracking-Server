#!/bin/bash
# Start GPS Tracking API and DB, and localtunnel with auto-restart

while true; do
  echo "[INFO] Starting Docker containers..."
  docker start gps-tracking-api gps-tracking-db
  sleep 3
  echo "[INFO] Starting localtunnel..."
  npx localtunnel --port 8000 --subdomain chatty-otter-15
  echo "[WARN] localtunnel exited. Restarting in 5 seconds..."
  sleep 5
done
