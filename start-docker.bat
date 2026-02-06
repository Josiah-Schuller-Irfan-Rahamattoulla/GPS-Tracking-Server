@echo off
cd /d "c:\Users\Irfan\Documents\Git\GPS-Tracking-Server"
docker-compose down
docker-compose up -d --build
docker-compose logs -f
