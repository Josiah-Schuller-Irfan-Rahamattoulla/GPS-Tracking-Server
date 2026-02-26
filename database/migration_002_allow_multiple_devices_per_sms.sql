-- Migration 002: Allow multiple devices per SMS number
-- One user/phone can have multiple devices; sms_number is the alert/contact number,
-- not a unique device identifier.
-- Run: psql $DATABASE_URI -f database/migration_002_allow_multiple_devices_per_sms.sql

ALTER TABLE devices DROP CONSTRAINT IF EXISTS devices_sms_number_key;
