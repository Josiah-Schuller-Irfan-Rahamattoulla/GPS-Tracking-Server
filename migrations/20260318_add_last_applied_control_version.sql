-- 2026-03-18: Reliable command recovery support

ALTER TABLE devices
ADD COLUMN IF NOT EXISTS last_applied_control_version INTEGER NOT NULL DEFAULT 0;

CREATE INDEX IF NOT EXISTS idx_devices_control_versions
ON devices (device_id, control_version, last_applied_control_version);
