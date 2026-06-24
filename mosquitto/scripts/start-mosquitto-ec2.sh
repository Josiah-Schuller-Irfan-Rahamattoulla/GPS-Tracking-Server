#!/bin/sh
set -e
mkdir -p /mosquitto/data/certs
cp /mosquitto/config/certs/ca.crt /mosquitto/config/certs/server.crt /mosquitto/config/certs/server.key /mosquitto/data/certs/
touch /mosquitto/config/passwd /mosquitto/config/acl
chown mosquitto:mosquitto /mosquitto/config/passwd /mosquitto/config/acl /mosquitto/data/certs/*
chmod 600 /mosquitto/config/passwd
chmod 644 /mosquitto/config/acl
exec /usr/sbin/mosquitto -c /mosquitto/config/mosquitto.conf
