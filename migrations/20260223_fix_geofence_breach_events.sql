-- Migration: alter geofence_breach_events to match model
ALTER TABLE geofence_breach_events
    RENAME COLUMN id TO event_id;

ALTER TABLE geofence_breach_events
    ADD COLUMN IF NOT EXISTS user_id INTEGER,
    ADD COLUMN IF NOT EXISTS notification_sent BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS notification_method VARCHAR(32),
    ADD COLUMN IF NOT EXISTS notification_sent_at TIMESTAMPTZ;

-- Add missing foreign key for user_id if needed
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE constraint_name = 'fk_user' AND table_name = 'geofence_breach_events'
    ) THEN
        ALTER TABLE geofence_breach_events
            ADD CONSTRAINT fk_user FOREIGN KEY(user_id) REFERENCES users(user_id) ON DELETE CASCADE;
    END IF;
END$$;
