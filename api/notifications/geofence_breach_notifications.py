import logging
import os
import smtplib
from email.message import EmailMessage
from typing import Iterable

from api.db.geofence_breaches import mark_breach_notification_sent
from api.db.models import Device, Geofence, GeofenceBreachEvent, User
from psycopg2.extensions import connection as PGConnection

logger = logging.getLogger(__name__)


def _env_bool(value: str | None) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "yes", "y", "on"}


def _smtp_settings() -> dict:
    return {
        "host": os.getenv("SMTP_HOST"),
        "port": int(os.getenv("SMTP_PORT", "587")),
        "username": os.getenv("SMTP_USERNAME"),
        "password": os.getenv("SMTP_PASSWORD"),
        "from_address": os.getenv("SMTP_FROM"),
        "use_tls": _env_bool(os.getenv("SMTP_USE_TLS", "true")),
        "enabled": _env_bool(os.getenv("NOTIFY_GEOFENCE_EMAIL", "false")),
    }


def _can_send_email(settings: dict, user: User | None) -> bool:
    if not settings["enabled"]:
        return False
    if not user or not user.email_address:
        return False
    if not settings["host"] or not settings["from_address"]:
        return False
    return True


def _send_email(settings: dict, to_address: str, subject: str, body: str) -> None:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings["from_address"]
    msg["To"] = to_address
    msg.set_content(body)

    with smtplib.SMTP(settings["host"], settings["port"]) as smtp:
        if settings["use_tls"]:
            smtp.starttls()
        if settings["username"]:
            smtp.login(settings["username"], settings["password"] or "")
        smtp.send_message(msg)


def _format_event_line(event: GeofenceBreachEvent, geofence: Geofence | None) -> str:
    geofence_label = geofence.name if geofence else f"Geofence #{event.geofence_id}"
    return (
        f"- {event.event_type} {geofence_label} at {event.event_time.isoformat()} "
        f"(lat {event.latitude:.6f}, lon {event.longitude:.6f})"
    )


def notify_geofence_breach_events(
    db_conn: PGConnection,
    events: Iterable[GeofenceBreachEvent],
    user: User | None,
    device: Device | None,
    geofences_by_id: dict[int, Geofence],
) -> None:
    settings = _smtp_settings()
    if not _can_send_email(settings, user):
        logger.debug("Geofence email notifications disabled or missing configuration.")
        return

    event_list = list(events)
    if not event_list:
        return

    device_label = device.name if device and device.name else f"Device #{event_list[0].device_id}"
    subject = f"Geofence alert for {device_label}"

    lines = [
        f"Geofence breach detected for {device_label}.",
        "",
        "Events:",
    ]
    for event in event_list:
        lines.append(_format_event_line(event, geofences_by_id.get(event.geofence_id)))

    body = "\n".join(lines)

    try:
        _send_email(settings, user.email_address, subject, body)
    except Exception:
        logger.exception("Failed to send geofence breach email notification")
        return

    for event in event_list:
        try:
            mark_breach_notification_sent(db_conn, event.event_id, "EMAIL")
        except Exception:
            logger.exception("Failed to mark notification sent for event %s", event.event_id)
