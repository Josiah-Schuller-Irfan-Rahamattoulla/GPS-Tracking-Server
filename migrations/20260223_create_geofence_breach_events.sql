-- Migration: create geofence_breach_events table
CREATE TABLE IF NOT EXISTS geofence_breach_events (
    id SERIAL PRIMARY KEY,
    device_id INTEGER NOT NULL,
    geofence_id INTEGER NOT NULL,
    event_type VARCHAR(32) NOT NULL, -- e.g., 'ENTERED', 'EXITED'
    event_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    speed DOUBLE PRECISION,
    extra JSONB,
    CONSTRAINT fk_device FOREIGN KEY(device_id) REFERENCES devices(device_id) ON DELETE CASCADE,
    CONSTRAINT fk_geofence FOREIGN KEY(geofence_id) REFERENCES geofences(geofence_id) ON DELETE CASCADE
);
