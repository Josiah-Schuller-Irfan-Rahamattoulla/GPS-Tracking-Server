-- Migration 003: Add geofence breach event tracking
-- Tracks when devices enter/exit geofences with notification status

CREATE TABLE IF NOT EXISTS geofence_breach_events (
    event_id SERIAL PRIMARY KEY,
    device_id INTEGER NOT NULL,
    geofence_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    event_type VARCHAR(20) NOT NULL CHECK (event_type IN ('ENTERED', 'EXITED')),
    latitude REAL NOT NULL,
    longitude REAL NOT NULL,
    event_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    notification_sent BOOLEAN DEFAULT FALSE,
    notification_method VARCHAR(50), -- 'SMS', 'EMAIL', 'PUSH', 'WEBHOOK'
    notification_sent_at TIMESTAMPTZ,
    FOREIGN KEY (device_id) REFERENCES devices(device_id) ON DELETE CASCADE,
    FOREIGN KEY (geofence_id) REFERENCES geofences(geofence_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

-- Add indexes for efficient querying
CREATE INDEX IF NOT EXISTS idx_breach_events_device ON geofence_breach_events(device_id, event_time DESC);
CREATE INDEX IF NOT EXISTS idx_breach_events_geofence ON geofence_breach_events(geofence_id, event_time DESC);
CREATE INDEX IF NOT EXISTS idx_breach_events_user ON geofence_breach_events(user_id, event_time DESC);
CREATE INDEX IF NOT EXISTS idx_breach_events_pending_notification ON geofence_breach_events(notification_sent, event_time) WHERE notification_sent = FALSE;

-- Add comments
COMMENT ON TABLE geofence_breach_events IS 'Log of geofence breach events (enter/exit) for devices';
COMMENT ON COLUMN geofence_breach_events.event_type IS 'Type of breach: ENTERED or EXITED';
COMMENT ON COLUMN geofence_breach_events.notification_sent IS 'Whether notification was successfully sent to user';
COMMENT ON COLUMN geofence_breach_events.notification_method IS 'Method used for notification delivery';
