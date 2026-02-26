-- Add tracking mode and upload intervals for devices
ALTER TABLE devices
    ADD COLUMN IF NOT EXISTS hot_mode BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS hot_upload_interval_ms INTEGER DEFAULT 5000,
    ADD COLUMN IF NOT EXISTS cold_upload_interval_ms INTEGER DEFAULT 120000,
    ADD COLUMN IF NOT EXISTS tracking_updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP;

UPDATE devices
SET hot_mode = COALESCE(hot_mode, FALSE),
    hot_upload_interval_ms = COALESCE(hot_upload_interval_ms, 5000),
    cold_upload_interval_ms = COALESCE(cold_upload_interval_ms, 120000),
    tracking_updated_at = COALESCE(tracking_updated_at, CURRENT_TIMESTAMP);
