-- Seed data for WebSocket tests (test_websocket.py).
-- Run against a running DB, e.g.:
--   psql "postgresql://gpsuser:gpspassword@localhost:5433/gps_tracking" -f database/seed_websocket_test_data.sql
-- Or from API container: psql "$DATABASE_URI" -f /path/to/seed_websocket_test_data.sql

-- Insert test user (access_token must match WS_USER_TOKEN in test_websocket.py)
INSERT INTO users (email_address, phone_number, name, salt, hashed_password, access_token)
VALUES (
  'ws-test@example.com',
  '+15550000000',
  'WebSocket Test User',
  'seedsalt',
  'dummyhashedpassword',
  'test-user-token'
)
ON CONFLICT (email_address) DO UPDATE SET access_token = EXCLUDED.access_token;

-- Insert test device (device_id will be 1 if table is empty; access_token must match WS_DEVICE_TOKEN)
INSERT INTO devices (device_id, access_token, sms_number)
VALUES (1, 'test-device-token', '+15550000001')
ON CONFLICT (device_id) DO UPDATE SET access_token = EXCLUDED.access_token;

-- Link user to device (user_id from the user we just upserted)
INSERT INTO users_devices (user_id, device_id)
SELECT u.user_id, 1 FROM users u WHERE u.access_token = 'test-user-token'
ON CONFLICT (user_id, device_id) DO NOTHING;
