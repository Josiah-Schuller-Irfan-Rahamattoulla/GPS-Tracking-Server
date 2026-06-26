"""
Provision Mosquitto credentials and ACL for a device (username=device_id, password=access_token).
"""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
import subprocess

from api.services.mqtt_client import mqtt_enabled
from api.services.mqtt_topics import (
    agnss_data_topic,
    cell_locate_response_topic,
    control_ack_topic,
    controls_topic,
    location_topic,
    reset_ack_topic,
    agnss_request_topic,
    cell_locate_request_topic,
)

logger = logging.getLogger(__name__)


def _passwd_file() -> str:
    return os.getenv("MQTT_PASSWD_FILE", "/mosquitto/config/passwd")


def _acl_file() -> str:
    return os.getenv("MQTT_ACL_FILE", "/mosquitto/config/acl")


def _device_acl_lines(device_id: int) -> list[str]:
    return [
        f"user {device_id}",
        f"topic read {controls_topic(device_id)}",
        f"topic read {agnss_data_topic(device_id)}",
        f"topic read {cell_locate_response_topic(device_id)}",
        f"topic write {location_topic(device_id)}",
        f"topic write {control_ack_topic(device_id)}",
        f"topic write {reset_ack_topic(device_id)}",
        f"topic write {agnss_request_topic(device_id)}",
        f"topic write {cell_locate_request_topic(device_id)}",
    ]


def upsert_device_acl(device_id: int) -> bool:
    """Replace per-device ACL block in the shared acl file."""
    acl_path = _acl_file()
    os.makedirs(os.path.dirname(acl_path), exist_ok=True)

    existing = ""
    if os.path.isfile(acl_path):
        existing = open(acl_path, encoding="utf-8").read()

    user_line = f"user {device_id}"
    filtered: list[str] = []
    skip = False
    for line in existing.splitlines():
        stripped = line.strip()
        if stripped == user_line:
            skip = True
            continue
        if skip:
            if stripped.startswith("user ") or stripped.startswith("pattern "):
                skip = False
            else:
                continue
        if not skip:
            filtered.append(line)

    while filtered and not filtered[-1].strip():
        filtered.pop()

    block = _device_acl_lines(device_id)
    if filtered:
        filtered.append("")
    filtered.extend(block)

    try:
        with open(acl_path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write("\n".join(filtered).rstrip() + "\n")
        logger.info("MQTT ACL updated device_id=%s", device_id)
        return True
    except OSError as exc:
        logger.warning("MQTT ACL update failed device_id=%s err=%s", device_id, exc)
        return False


def provision_mqtt_device(device_id: int, access_token: str) -> bool:
    """
    Add or update device credentials in the Mosquitto password file and ACL.

    Requires mosquitto_passwd on PATH (mosquitto-clients package in API image).
    Reload Mosquitto (SIGHUP) after batch updates so passwd/acl take effect.
    """
    if not mqtt_enabled():
        return False
    if not access_token:
        logger.warning("MQTT provision skipped: empty access_token device_id=%s", device_id)
        return False

    passwd_bin = shutil.which("mosquitto_passwd")
    if passwd_bin is None:
        logger.warning("MQTT provision skipped: mosquitto_passwd not found on PATH")
        return False

    passwd_file = _passwd_file()
    os.makedirs(os.path.dirname(passwd_file), exist_ok=True)

    try:
        subprocess.run(
            [passwd_bin, "-b", passwd_file, str(device_id), access_token],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        logger.warning(
            "MQTT provision failed device_id=%s rc=%s stderr=%s",
            device_id,
            exc.returncode,
            (exc.stderr or "").strip(),
        )
        return False

    upsert_device_acl(device_id)
    logger.info(
        "MQTT credentials provisioned device_id=%s (SIGHUP mosquitto to reload passwd/acl)",
        device_id,
    )
    return True


async def provision_mqtt_device_async(device_id: int, access_token: str) -> bool:
    return await asyncio.to_thread(provision_mqtt_device, device_id, access_token)
