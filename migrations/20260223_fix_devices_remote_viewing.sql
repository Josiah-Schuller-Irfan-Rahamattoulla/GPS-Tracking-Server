-- Migration: ensure all devices have remote_viewing and last_viewed_at columns
ALTER TABLE devices
    ADD COLUMN IF NOT EXISTS remote_viewing BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS last_viewed_at TIMESTAMPTZ;

UPDATE devices SET remote_viewing = COALESCE(remote_viewing, FALSE);
