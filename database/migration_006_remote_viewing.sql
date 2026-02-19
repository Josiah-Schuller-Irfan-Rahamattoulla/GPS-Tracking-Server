-- Add remote_viewing flag for when web/app is actively viewing device
ALTER TABLE devices
    ADD COLUMN IF NOT EXISTS remote_viewing BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS last_viewed_at TIMESTAMPTZ;

UPDATE devices
SET remote_viewing = COALESCE(remote_viewing, FALSE);

COMMENT ON COLUMN devices.remote_viewing IS 'True when web/app is actively viewing this device (triggers hot mode)';
COMMENT ON COLUMN devices.last_viewed_at IS 'Timestamp when device was last viewed from web/app';
