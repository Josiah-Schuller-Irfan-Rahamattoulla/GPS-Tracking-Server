-- Migration 004: Notification Audit Log
-- Tracks all notification attempts for geofence breach events

CREATE TABLE IF NOT EXISTS notification_audit_log (
    log_id SERIAL PRIMARY KEY,
    breach_event_id INTEGER NOT NULL REFERENCES geofence_breach_events(event_id) ON DELETE CASCADE,
    notification_type VARCHAR(20) NOT NULL, -- 'EMAIL', 'SMS', 'PUSH', 'WEBHOOK'
    recipient VARCHAR(255) NOT NULL, -- Email address, phone number, device token, or webhook URL
    status VARCHAR(20) NOT NULL, -- 'PENDING', 'SENT', 'FAILED', 'RETRYING'
    attempt_count INTEGER NOT NULL DEFAULT 1,
    error_message TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    sent_at TIMESTAMP,
    next_retry_at TIMESTAMP
);

CREATE INDEX idx_notification_audit_breach ON notification_audit_log(breach_event_id);
CREATE INDEX idx_notification_audit_status ON notification_audit_log(status);
CREATE INDEX idx_notification_audit_retry ON notification_audit_log(next_retry_at) WHERE status = 'RETRYING';

-- Add comment
COMMENT ON TABLE notification_audit_log IS 'Audit trail for all notification attempts with retry tracking';
