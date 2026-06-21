"""
Provision Mosquitto credentials for a device (username=device_id, password=access_token).
"""

from __future__ import annotations

import asyncio
import logging
import os
import shutil
import subprocess

from api.services.mqtt_client import mqtt_enabled

logger = logging.getLogger(__name__)


def _passwd_file() -> str:
    return os.getenv("MQTT_PASSWD_FILE", "/mosquitto/config/passwd")


def provision_mqtt_device(device_id: int, access_token: str) -> bool:
    """
    Add or update device credentials in the Mosquitto password file.

    Requires mosquitto_passwd on PATH (mosquitto-clients package in API image).
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
        logger.info("MQTT credentials provisioned device_id=%s", device_id)
        return True
    except subprocess.CalledProcessError as exc:
        logger.warning(
            "MQTT provision failed device_id=%s rc=%s stderr=%s",
            device_id,
            exc.returncode,
            (exc.stderr or "").strip(),
        )
        return False


async def provision_mqtt_device_async(device_id: int, access_token: str) -> bool:
    return await asyncio.to_thread(provision_mqtt_device, device_id, access_token)
