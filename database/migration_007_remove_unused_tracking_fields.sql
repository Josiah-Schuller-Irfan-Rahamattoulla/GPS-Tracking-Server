-- Migration 007: Remove unused tracking interval fields
-- The firmware hardcodes upload intervals (5s HOT, 120s COLD)
-- Only remote_viewing is actually checked by the device
-- Keep remote_viewing + last_viewed_at, remove the rest

ALTER TABLE devices 
DROP COLUMN IF EXISTS hot_mode,
DROP COLUMN IF EXISTS hot_upload_interval_ms,
DROP COLUMN IF EXISTS cold_upload_interval_ms,
DROP COLUMN IF EXISTS tracking_updated_at;

COMMENT ON COLUMN devices.remote_viewing IS 'True when user is actively viewing device via web/app - triggers HOT mode';
COMMENT ON COLUMN devices.last_viewed_at IS 'Timestamp when remote_viewing was last set to true';
