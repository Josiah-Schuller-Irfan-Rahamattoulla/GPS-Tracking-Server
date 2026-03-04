"""
SMS notification service for geofence breach events.
Supports Twilio and AWS SNS backends.
"""

import logging
import os
from typing import Iterable

from api.db.geofence_breaches import mark_breach_notification_sent
from api.db.models import Device, Geofence, GeofenceBreachEvent, User
from psycopg2.extensions import connection as PGConnection

logger = logging.getLogger(__name__)


def _env_bool(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on"}


class SMSNotificationProvider:
    """Base class for SMS notification providers."""
    
    def send(self, to_phone: str, message: str) -> bool:
        """Send SMS message. Returns True if successful."""
        raise NotImplementedError()


class TwilioSMSProvider(SMSNotificationProvider):
    """Twilio SMS provider."""
    
    def __init__(self):
        self.account_sid = os.getenv("TWILIO_ACCOUNT_SID")
        self.auth_token = os.getenv("TWILIO_AUTH_TOKEN")
        self.from_phone = os.getenv("TWILIO_FROM_PHONE")
        self.enabled = _env_bool(os.getenv("NOTIFY_GEOFENCE_SMS_TWILIO", "false"))
        
        if self.enabled and (not self.account_sid or not self.auth_token or not self.from_phone):
            logger.warning("Twilio SMS notifications enabled but missing configuration")
            self.enabled = False
    
    def send(self, to_phone: str, message: str) -> bool:
        """Send SMS via Twilio."""
        if not self.enabled:
            return False
        
        try:
            from twilio.rest import Client
            client = Client(self.account_sid, self.auth_token)
            msg = client.messages.create(
                body=message,
                from_=self.from_phone,
                to=to_phone
            )
            logger.info(f"Sent SMS via Twilio to {to_phone}, SID: {msg.sid}")
            return True
        except ImportError:
            logger.error("Twilio SDK not installed. Install with: pip install twilio")
            return False
        except Exception as e:
            logger.error(f"Failed to send SMS via Twilio: {e}")
            return False


class AWSSNSSMS(SMSNotificationProvider):
    """AWS SNS SMS provider."""
    
    def __init__(self):
        self.enabled = _env_bool(os.getenv("NOTIFY_GEOFENCE_SMS_AWS", "false"))
        self.region = os.getenv("AWS_REGION", "us-east-1")
        
        if self.enabled:
            # AWS SDK will use credentials from environment or IAM role
            pass
    
    def send(self, to_phone: str, message: str) -> bool:
        """Send SMS via AWS SNS."""
        if not self.enabled:
            return False
        
        try:
            import boto3
            client = boto3.client("sns", region_name=self.region)
            response = client.publish(
                PhoneNumber=to_phone,
                Message=message,
                MessageAttributes={
                    "AWS.SNS.SMS.SenderID": {
                        "DataType": "String",
                        "StringValue": "GPSTracker"
                    }
                }
            )
            logger.info(f"Sent SMS via AWS SNS to {to_phone}, MessageId: {response['MessageId']}")
            return True
        except ImportError:
            logger.error("AWS SDK not installed. Install with: pip install boto3")
            return False
        except Exception as e:
            logger.error(f"Failed to send SMS via AWS SNS: {e}")
            return False


def get_sms_provider() -> SMSNotificationProvider | None:
    """Get the configured SMS provider."""
    # Try Twilio first
    twilio = TwilioSMSProvider()
    if twilio.enabled:
        return twilio
    
    # Try AWS SNS
    aws = AWSSNSSMS()
    if aws.enabled:
        return aws
    
    return None


def _format_sms_message(events: list[GeofenceBreachEvent], device: Device | None, geofences_by_id: dict) -> str:
    """Format a concise SMS message for geofence breach events."""
    device_label = device.name if device and device.name else f"Device {events[0].device_id}"
    
    # Keep SMS short (160 chars is ideal)
    event_summary = ", ".join([
        f"{e.event_type} {geofences_by_id.get(e.geofence_id, {}).name or f'GF{e.geofence_id}'}"
        for e in events[:2]  # Only first 2 events to keep it short
    ])
    
    if len(events) > 2:
        event_summary += f" +{len(events)-2} more"
    
    return f"GPS Alert: {device_label} - {event_summary}"


def notify_geofence_breach_via_sms(
    db_conn: PGConnection,
    events: Iterable[GeofenceBreachEvent],
    user: User | None,
    device: Device | None,
    geofences_by_id: dict[int, Geofence],
) -> None:
    """Send SMS notifications for geofence breach events."""
    provider = get_sms_provider()
    if not provider:
        logger.debug("SMS notifications disabled or not configured.")
        return
    
    if not user or not device or not device.sms_number:
        logger.debug("Cannot send SMS: missing user, device, or SMS number")
        return
    
    event_list = list(events)
    if not event_list:
        return
    
    message = _format_sms_message(event_list, device, geofences_by_id)
    
    try:
        if provider.send(device.sms_number, message):
            # Mark all events as notified
            for event in event_list:
                try:
                    mark_breach_notification_sent(db_conn, event.event_id, "SMS")
                except Exception as e:
                    logger.error(f"Failed to mark notification sent for event {event.event_id}: {e}")
        else:
            logger.warning(f"Failed to send SMS to {device.sms_number}")
    except Exception as e:
        logger.exception(f"Error sending SMS notifications: {e}")
