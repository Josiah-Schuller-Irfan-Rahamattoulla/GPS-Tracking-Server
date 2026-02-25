-- Migration: Make remote_viewing NOT NULL with default FALSE
ALTER TABLE devices
    ALTER COLUMN remote_viewing SET NOT NULL,
    ALTER COLUMN remote_viewing SET DEFAULT FALSE;
