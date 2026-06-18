-- Remote reboot: app bumps reset_token; device polls getDeviceControls and ACKs after reboot.

ALTER TABLE devices
ADD COLUMN IF NOT EXISTS reset_token INTEGER NOT NULL DEFAULT 0;

ALTER TABLE devices
ADD COLUMN IF NOT EXISTS reset_applied_token INTEGER NOT NULL DEFAULT 0;

COMMENT ON COLUMN devices.reset_token IS 'Incremented when user requests tracker reboot';
COMMENT ON COLUMN devices.reset_applied_token IS 'Last reset_token ACKed by firmware before reboot';
