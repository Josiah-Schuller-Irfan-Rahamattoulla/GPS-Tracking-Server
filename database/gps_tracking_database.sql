-- GPS Tracking Database Schema for PostgreSQL
-- Generated from ERD diagram

-- Drop tables if they exist (for clean recreation)
DROP TABLE IF EXISTS gps_data CASCADE;
DROP TABLE IF EXISTS users_devices CASCADE;
DROP TABLE IF EXISTS devices CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- Create users table
CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,
    email_address VARCHAR(255) NOT NULL UNIQUE,
    phone_number VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    salt VARCHAR(255) NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    access_token VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create devices table
CREATE TABLE devices (
    device_id SERIAL PRIMARY KEY,
    access_token VARCHAR(255) NOT NULL,
    sms_number VARCHAR(20) NOT NULL UNIQUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    control_1 BOOLEAN NOT NULL DEFAULT FALSE,
    control_2 BOOLEAN NOT NULL DEFAULT FALSE,
    control_3 BOOLEAN NOT NULL DEFAULT FALSE,
    control_4 BOOLEAN NOT NULL DEFAULT FALSE
);

-- Create users_devices junction table (many-to-many relationship)
CREATE TABLE users_devices (
    user_id INTEGER NOT NULL,
    device_id INTEGER NOT NULL,
    PRIMARY KEY (user_id, device_id),
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (device_id) REFERENCES devices(device_id) ON DELETE CASCADE
);

-- Create gps_data table
CREATE TABLE gps_data (
    device_id INTEGER NOT NULL,
    time TIMESTAMPTZ NOT NULL,
    latitude REAL,
    longitude REAL,
    PRIMARY KEY (device_id, time),
    FOREIGN KEY (device_id) REFERENCES devices(device_id) ON DELETE CASCADE
);

-- Create indexes for better performance
CREATE INDEX idx_users_email ON users(email_address);
CREATE INDEX idx_users_access_token ON users(access_token);
CREATE INDEX idx_devices_sms_number ON devices(sms_number);
CREATE INDEX idx_gps_data_time ON gps_data(time);
CREATE INDEX idx_gps_data_device_time ON gps_data(device_id, time DESC);

-- Add comments to tables and columns for documentation
COMMENT ON TABLE users IS 'User accounts with authentication information';
COMMENT ON COLUMN users.user_id IS 'Primary key - unique user identifier';
COMMENT ON COLUMN users.email_address IS 'User email address (must be unique)';
COMMENT ON COLUMN users.phone_number IS 'User phone number';
COMMENT ON COLUMN users.name IS 'User full name';
COMMENT ON COLUMN users.salt IS 'Salt used for password hashing';
COMMENT ON COLUMN users.hashed_password IS 'Hashed password for authentication';
COMMENT ON COLUMN users.access_token IS 'API access token for user';
COMMENT ON COLUMN users.created_at IS 'Timestamp when user account was created';

COMMENT ON TABLE devices IS 'GPS tracking devices';
COMMENT ON COLUMN devices.device_id IS 'Primary key - unique device identifier';
COMMENT ON COLUMN devices.sms_number IS 'SMS number for device communication (must be unique)';
COMMENT ON COLUMN devices.created_at IS 'Timestamp when device was registered';
COMMENT ON COLUMN devices.control_1 IS 'Device control setting 1';
COMMENT ON COLUMN devices.control_2 IS 'Device control setting 2';
COMMENT ON COLUMN devices.control_3 IS 'Device control setting 3';
COMMENT ON COLUMN devices.control_4 IS 'Device control setting 4';

COMMENT ON TABLE users_devices IS 'Junction table linking users to their devices (many-to-many)';
COMMENT ON COLUMN users_devices.user_id IS 'Foreign key reference to users table';
COMMENT ON COLUMN users_devices.device_id IS 'Foreign key reference to devices table';

COMMENT ON TABLE gps_data IS 'GPS location data from tracking devices';
COMMENT ON COLUMN gps_data.device_id IS 'Foreign key reference to devices table';
COMMENT ON COLUMN gps_data.time IS 'Timestamp when GPS data was recorded';
COMMENT ON COLUMN gps_data.latitude IS 'GPS latitude coordinate';
COMMENT ON COLUMN gps_data.longitude IS 'GPS longitude coordinate';
