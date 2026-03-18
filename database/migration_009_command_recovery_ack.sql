-- Migration 009: Reliable command recovery support (device ACK + pending detection)

-- Track the latest control revision that the device has actually applied.
ALTER TABLE devices
ADD COLUMN IF NOT EXISTS last_applied_control_version INTEGER NOT NULL DEFAULT 0;

CREATE INDEX IF NOT EXISTS idx_devices_control_versions
ON devices (device_id, control_version, last_applied_control_version);

COMMENT ON COLUMN devices.last_applied_control_version IS
'Device-confirmed applied control revision for reliable command reconciliation';
