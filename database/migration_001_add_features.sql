-- Migration 001: Add missing features for concurrent access
-- Run this migration to add: GPS extensions, device name, geofences, control versioning

-- 1. Add GPS data extensions (speed, heading, trip_active)
ALTER TABLE gps_data 
ADD COLUMN IF NOT EXISTS speed REAL,
ADD COLUMN IF NOT EXISTS heading REAL,
ADD COLUMN IF NOT EXISTS trip_active BOOLEAN DEFAULT FALSE;

-- Add index for trip_active queries
CREATE INDEX IF NOT EXISTS idx_gps_data_trip_active ON gps_data(device_id, trip_active) WHERE trip_active = TRUE;

-- 2. Add device name field
ALTER TABLE devices ADD COLUMN IF NOT EXISTS name VARCHAR(100);

-- 3. Add device control versioning for conflict resolution
ALTER TABLE devices 
ADD COLUMN IF NOT EXISTS control_version INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS controls_updated_at TIMESTAMPTZ;

-- 4. Create geofences table
CREATE TABLE IF NOT EXISTS geofences (
    geofence_id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL,
    name VARCHAR(100) NOT NULL,
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    radius REAL NOT NULL DEFAULT 100, -- meters
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Add indexes for geofences
CREATE INDEX IF NOT EXISTS idx_geofences_user ON geofences(user_id);
CREATE INDEX IF NOT EXISTS idx_geofences_enabled ON geofences(user_id, enabled) WHERE enabled = TRUE;

-- Add comments
COMMENT ON COLUMN gps_data.speed IS 'Vehicle speed in km/h';
COMMENT ON COLUMN gps_data.heading IS 'Compass heading in degrees (0-360)';
COMMENT ON COLUMN gps_data.trip_active IS 'Hardware IMU-detected trip status';
COMMENT ON COLUMN devices.name IS 'User-friendly device name';
COMMENT ON COLUMN devices.control_version IS 'Version number for optimistic locking on control updates';
COMMENT ON COLUMN devices.controls_updated_at IS 'Timestamp of last control update';
COMMENT ON TABLE geofences IS 'Geofence definitions for users';
























































