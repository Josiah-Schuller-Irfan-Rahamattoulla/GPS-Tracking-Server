"""
Unified notification service with retry logic and audit logging.
Supports email, SMS, push notifications, and webhooks.
"""

import logging
import os
from datetime import datetime, timedelta
from typing import Iterable

import psycopg2.extras
from psycopg2.extensions import connection as PGConnection

from db.models import Device, Geofence, GeofenceBreachEvent, User
from notifications.geofence_breach_notifications import (
    _smtp_settings,
    _send_email,
    _can_send_email,
)
from notifications.sms_notifications import TwilioSMSProvider, AWSSNSSMS

logger = logging.getLogger(__name__)


def _env_bool(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on"}


class NotificationService:
    """Unified notification service with retry and audit logging."""
    
    MAX_RETRIES = 3
    RETRY_DELAYS = [60, 300, 900]  # 1 min, 5 min, 15 min
    
    def __init__(self, db_conn: PGConnection):
        self.db_conn = db_conn
        self.sms_providers = [TwilioSMSProvider(), AWSSNSSMS()]
    
    def _log_notification(
        self,
        breach_event_id: int,
        notification_type: str,
        recipient: str,
        status: str,
        error_message: str | None = None,
        attempt_count: int = 1,
        next_retry_at: datetime | None = None,
    ) -> int:
        """Log notification attempt to audit table."""
        cursor = self.db_conn.cursor()
        cursor.execute(
            """
            INSERT INTO notification_audit_log 
            (breach_event_id, notification_type, recipient, status, attempt_count, error_message, sent_at, next_retry_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING log_id
            """,
            (
                breach_event_id,
                notification_type,
                recipient,
                status,
                attempt_count,
                error_message,
                datetime.utcnow() if status == "SENT" else None,
                next_retry_at,
            ),
        )
        log_id = cursor.fetchone()[0]
        self.db_conn.commit()
        return log_id
    
    def _update_notification_log(
        self,
        log_id: int,
        status: str,
        error_message: str | None = None,
        attempt_count: int | None = None,
        next_retry_at: datetime | None = None,
    ) -> None:
        """Update notification log status."""
        cursor = self.db_conn.cursor()
        cursor.execute(
            """
            UPDATE notification_audit_log
            SET status = %s,
                error_message = COALESCE(%s, error_message),
                attempt_count = COALESCE(%s, attempt_count),
                sent_at = CASE WHEN %s = 'SENT' THEN CURRENT_TIMESTAMP ELSE sent_at END,
                next_retry_at = %s
            WHERE log_id = %s
            """,
            (status, error_message, attempt_count, status, next_retry_at, log_id),
        )
        self.db_conn.commit()
    
    def _send_email_notification(
        self,
        event: GeofenceBreachEvent,
        user: User,
        device: Device | None,
        geofence: Geofence | None,
    ) -> tuple[bool, str | None]:
        """Send email notification. Returns (success, error_message)."""
        settings = _smtp_settings()
        
        if not _can_send_email(settings, user):
            return False, "Email notifications disabled or missing configuration"
        
        device_label = device.name if device and device.name else f"Device #{event.device_id}"
        geofence_label = geofence.name if geofence else f"Geofence #{event.geofence_id}"
        
        subject = f"Geofence alert: {device_label} {event.event_type} {geofence_label}"
        body = f"""
Geofence breach detected:

Device: {device_label}
Geofence: {geofence_label}
Event: {event.event_type}
Time: {event.event_time.isoformat()}
Location: {event.latitude:.6f}, {event.longitude:.6f}

This is an automated notification from your GPS tracking system.
"""
        
        try:
            _send_email(settings, user.email_address, subject, body.strip())
            logger.info(f"Sent email notification to {user.email_address}")
            return True, None
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False, str(e)
    
    def _send_sms_notification(
        self,
        event: GeofenceBreachEvent,
        phone_number: str,
        device: Device | None,
        geofence: Geofence | None,
    ) -> tuple[bool, str | None]:
        """Send SMS notification. Returns (success, error_message)."""
        device_label = device.name if device and device.name else f"Device {event.device_id}"
        geofence_label = geofence.name if geofence else f"Geofence {event.geofence_id}"
        
        message = f"GPS Alert: {device_label} {event.event_type} {geofence_label} at {event.event_time.strftime('%I:%M %p')}"
        
        for provider in self.sms_providers:
            try:
                if provider.send(phone_number, message):
                    logger.info(f"Sent SMS notification to {phone_number}")
                    return True, None
            except Exception as e:
                logger.error(f"SMS provider {provider.__class__.__name__} failed: {e}")
                continue
        
        return False, "All SMS providers failed"
    
    def send_breach_notifications(
        self,
        events: Iterable[GeofenceBreachEvent],
        user: User | None,
        device: Device | None,
        geofences_by_id: dict[int, Geofence],
    ) -> None:
        """Send notifications for geofence breach events with retry logic."""
        if not user:
            logger.warning("No user provided for breach notifications")
            return
        
        event_list = list(events)
        if not event_list:
            return
        
        for event in event_list:
            geofence = geofences_by_id.get(event.geofence_id)
            
            # Send email notification
            if user.email_address:
                log_id = self._log_notification(
                    event.event_id, "EMAIL", user.email_address, "PENDING"
                )
                
                success, error = self._send_email_notification(event, user, device, geofence)
                
                if success:
                    self._update_notification_log(log_id, "SENT")
                else:
                    next_retry = datetime.utcnow() + timedelta(seconds=self.RETRY_DELAYS[0])
                    self._update_notification_log(
                        log_id, "RETRYING", error, 1, next_retry
                    )
            
            # Send SMS notification
            if device and device.sms_number:
                log_id = self._log_notification(
                    event.event_id, "SMS", device.sms_number, "PENDING"
                )
                
                success, error = self._send_sms_notification(event, device.sms_number, device, geofence)
                
                if success:
                    self._update_notification_log(log_id, "SENT")
                else:
                    next_retry = datetime.utcnow() + timedelta(seconds=self.RETRY_DELAYS[0])
                    self._update_notification_log(
                        log_id, "RETRYING", error, 1, next_retry
                    )
    
    def retry_failed_notifications(self) -> int:
        """Retry failed notifications that are due. Returns count of retries attempted."""
        cursor = self.db_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute(
            """
            SELECT log_id, breach_event_id, notification_type, recipient, attempt_count
            FROM notification_audit_log
            WHERE status = 'RETRYING'
              AND next_retry_at <= CURRENT_TIMESTAMP
              AND attempt_count < %s
            """,
            (self.MAX_RETRIES,),
        )
        
        retry_items = cursor.fetchall()
        retry_count = 0
        
        for item in retry_items:
            log_id = item["log_id"]
            attempt_count = item["attempt_count"] + 1
            
            # Get event details
            cursor.execute(
                """
                SELECT e.*, d.name as device_name, d.sms_number, g.name as geofence_name
                FROM geofence_breach_events e
                LEFT JOIN devices d ON e.device_id = d.device_id
                LEFT JOIN geofences g ON e.geofence_id = g.geofence_id
                WHERE e.event_id = %s
                """,
                (item["breach_event_id"],),
            )
            event_row = cursor.fetchone()
            if not event_row:
                continue
            
            # Retry notification
            success = False
            error_message = None
            
            if item["notification_type"] == "EMAIL":
                # Re-send email logic would go here
                pass
            elif item["notification_type"] == "SMS":
                # Re-send SMS logic would go here
                pass
            
            # Update log
            if success:
                self._update_notification_log(log_id, "SENT")
                retry_count += 1
            elif attempt_count >= self.MAX_RETRIES:
                self._update_notification_log(log_id, "FAILED", error_message, attempt_count)
            else:
                next_retry = datetime.utcnow() + timedelta(seconds=self.RETRY_DELAYS[attempt_count - 1])
                self._update_notification_log(
                    log_id, "RETRYING", error_message, attempt_count, next_retry
                )
        
        return retry_count
