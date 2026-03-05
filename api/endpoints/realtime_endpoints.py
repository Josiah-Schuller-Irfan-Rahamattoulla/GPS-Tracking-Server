"""Real-time WebSocket endpoints for live location streaming and notifications."""

import json
import asyncio
import os
import time
import logging
from typing import Dict, Set, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from datetime import datetime
from psycopg2 import connect

from api.db.devices import get_device, get_user_ids_for_device
from api.db.users import get_user_by_access_token
from api.services.device_ingest import ingest_location

logger = logging.getLogger(__name__)
router = APIRouter()


class ConnectionManager:
    """Manages WebSocket connections grouped by room (device or user subscriptions)."""

    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.room_metadata: Dict[str, dict] = {}

    async def connect(self, room: str, websocket: WebSocket, metadata: Optional[dict] = None):
        """Add a new WebSocket connection to a room."""
        if room not in self.active_connections:
            self.active_connections[room] = set()
            self.room_metadata[room] = metadata or {}
        
        self.active_connections[room].add(websocket)
        await websocket.accept()
        logger.info(f"Client connected to room '{room}'. Total connections: {len(self.active_connections[room])}")

    async def disconnect(self, room: str, websocket: WebSocket):
        """Remove a WebSocket connection from a room."""
        if room in self.active_connections:
            self.active_connections[room].discard(websocket)
            logger.info(f"Client disconnected from room '{room}'. Remaining: {len(self.active_connections[room])}")
            
            # Cleanup empty rooms
            if not self.active_connections[room]:
                del self.active_connections[room]
                del self.room_metadata[room]

    async def broadcast_to_room(self, room: str, message: dict) -> int:
        """
        Send message to all connections in a room.
        Returns number of successful sends.
        """
        if room not in self.active_connections:
            return 0

        disconnected = set()
        success_count = 0

        for connection in self.active_connections[room]:
            try:
                await connection.send_json(message)
                success_count += 1
            except Exception as e:
                logger.warning(f"Error sending to room '{room}': {e}")
                disconnected.add(connection)

        # Cleanup disconnected clients
        for conn in disconnected:
            await self.disconnect(room, conn)

        return success_count

    async def broadcast_except(self, room: str, message: dict, exclude_ws: WebSocket) -> int:
        """Send message to all connections in a room except one."""
        if room not in self.active_connections:
            return 0

        success_count = 0
        for connection in self.active_connections[room]:
            if connection != exclude_ws:
                try:
                    await connection.send_json(message)
                    success_count += 1
                except Exception as e:
                    logger.warning(f"Error sending to room '{room}': {e}")

        return success_count

    def get_room_stats(self, room: str) -> dict:
        """Get connection statistics for a room."""
        count = len(self.active_connections.get(room, set()))
        return {
            "room": room,
            "active_connections": count,
            "metadata": self.room_metadata.get(room, {})
        }


# Global connection manager
manager = ConnectionManager()


@router.websocket("/ws/devices/{device_id}")
async def websocket_device_stream(
    websocket: WebSocket,
    device_id: int,
    token: str = Query(None)
):
    """
    WebSocket endpoint for device real-time communication.
    Device connects here to send location updates and receive control commands.
    
    Query params:
    - token: Device authentication token
    """
    if not token:
        logger.warning(f"WebSocket device {device_id} rejected: missing token")
        await websocket.close(code=1008, reason="Missing device token")
        await asyncio.sleep(0.05)  # Ensure close frame is sent
        return

    db_conn = connect(dsn=os.getenv("DATABASE_URI"))
    try:
        device = get_device(db_conn=db_conn, device_id=device_id)
        if device is None or device.access_token != token:
            logger.warning(f"WebSocket device {device_id} rejected: invalid token")
            await websocket.close(code=1008, reason="Invalid device or token")
            await asyncio.sleep(0.05)
            return
    finally:
        db_conn.close()

    room = f"device_{device_id}"
    await manager.connect(room, websocket, {"device_id": device_id, "type": "device"})

    # Send current controls immediately so any updates made while device was disconnected are applied (no control downtime).
    # Re-fetch from DB so welcome always has the very latest state.
    try:
        db_conn_welcome = connect(dsn=os.getenv("DATABASE_URI"))
        try:
            device_latest = get_device(db_conn=db_conn_welcome, device_id=device_id)
        finally:
            db_conn_welcome.close()
        welcome_msg = {
            "type": "device_control_response",
            "device_id": device_id,
            "timestamp": int(time.time() * 1000),
            "data": {},
        }
        if device_latest:
            for key in ("control_1", "control_2", "control_3", "control_4", "control_version", "controls_updated_at"):
                val = getattr(device_latest, key, None)
                if val is not None:
                    welcome_msg[key] = val.isoformat() if hasattr(val, "isoformat") else val
            # Ensure all four controls are always present so device never merges with stale state
            for key in ("control_1", "control_2", "control_3", "control_4"):
                if key not in welcome_msg:
                    welcome_msg[key] = False
        await websocket.send_json(welcome_msg)
        logger.debug(f"Device {device_id}: sent welcome controls on connect (latest from DB)")
    except Exception as e:
        logger.warning(f"Device {device_id}: failed to send welcome controls: {e}")

    # Idle timeout: close if device sends nothing for 2 min (device pings ~every 10s when idle)
    DEVICE_WS_RECV_TIMEOUT = 120

    try:
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=DEVICE_WS_RECV_TIMEOUT)
            except asyncio.TimeoutError:
                logger.warning(f"Device {device_id} WebSocket idle timeout ({DEVICE_WS_RECV_TIMEOUT}s), closing")
                await manager.disconnect(room, websocket)
                try:
                    await websocket.close(code=1000, reason="Idle timeout")
                except Exception:
                    pass
                return
            message = json.loads(data)
            
            if message.get("type") == "ping":
                await websocket.send_json({
                    "type": "pong",
                    "timestamp": int(time.time() * 1000)
                })
            
            elif message.get("type") == "location_update":
                # Persist and geofence (same as HTTP sendGPSData), then broadcast
                data = message.get("data") or message
                if isinstance(data, dict) and data.get("latitude") is not None and data.get("longitude") is not None:
                    try:
                        location_data, breach_events = await asyncio.to_thread(
                            ingest_location, device_id, data
                        )
                        await broadcast_location_update(device_id, location_data)
                        ts = location_data.get("created_at", "")
                        lat, lon = location_data["latitude"], location_data["longitude"]
                        for breach_event in breach_events:
                            breach_data = {
                                "device_id": device_id,
                                "geofence_id": breach_event.geofence_id,
                                "latitude": lat,
                                "longitude": lon,
                                "breached_at": ts,
                            }
                            await broadcast_geofence_breach(device_id, breach_event.geofence_id, breach_data)
                        logger.debug(f"Location update from device {device_id} ingested and broadcasted")
                    except ValueError as e:
                        logger.warning(f"Device {device_id} location_update invalid: {e}")
                else:
                    # No persist: forward as before for backwards compatibility
                    broadcast_msg = {
                        "type": "location_update",
                        "device_id": device_id,
                        "data": message.get("data", {}),
                        "timestamp": int(time.time() * 1000)
                    }
                    await manager.broadcast_to_room(f"user_device_{device_id}", broadcast_msg)
                    logger.debug(f"Location update from device {device_id} broadcasted (no persist)")

            elif message.get("type") == "control_applied":
                # Tracker confirms it applied controls (e.g. kill switch); forward to app/website for feedback
                broadcast_msg = {
                    "type": "control_applied",
                    "device_id": device_id,
                    "control_1": message.get("control_1"),
                    "control_2": message.get("control_2"),
                    "control_3": message.get("control_3"),
                    "control_4": message.get("control_4"),
                    "timestamp": int(time.time() * 1000),
                }
                await manager.broadcast_to_room(f"user_device_{device_id}", broadcast_msg)
                logger.debug(f"Device {device_id} control_applied broadcasted to users")
            
            else:
                logger.warning(f"Unknown message type from device {device_id}: {message.get('type')}")

    except WebSocketDisconnect:
        await manager.disconnect(room, websocket)
        logger.info(f"Device {device_id} WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error (device {device_id}): {e}")
        await manager.disconnect(room, websocket)


@router.websocket("/ws/users/{device_id}")
async def websocket_user_stream(
    websocket: WebSocket,
    device_id: int,
    token: str = Query(None)
):
    """
    WebSocket endpoint for users watching device real-time locations.
    Users connect here to receive live updates for a specific device.
    
    Query params:
    - token: User authentication token
    """
    if not token:
        await websocket.close(code=1008, reason="Missing auth token")
        return

    db_conn = connect(dsn=os.getenv("DATABASE_URI"))
    try:
        user = get_user_by_access_token(db_conn, token)
        if user is None:
            await websocket.close(code=1008, reason="Invalid user token")
            return
        user_ids_with_access = get_user_ids_for_device(db_conn, device_id)
        if user.user_id not in user_ids_with_access:
            await websocket.close(code=1008, reason="No access to this device")
            return
    finally:
        db_conn.close()

    room = f"user_device_{device_id}"
    await manager.connect(room, websocket, {"device_id": device_id, "type": "user", "user_id": user.user_id})

    try:
        last_ping = time.time()
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            if message.get("type") == "ping":
                last_ping = time.time()
                await websocket.send_json({
                    "type": "pong",
                    "timestamp": int(time.time() * 1000)
                })

            elif message.get("type") == "subscribe_geofence":
                # User subscribed to geofence alerts for this device
                geofence_room = f"geofence_{device_id}"
                await manager.connect(geofence_room, websocket, {"device_id": device_id, "type": "geofence_subscriber"})
                logger.info(f"User subscribed to geofence alerts for device {device_id}")

            else:
                logger.debug(f"Message from user for device {device_id}: {message.get('type')}")

    except WebSocketDisconnect:
        await manager.disconnect(room, websocket)
        logger.info(f"User WebSocket for device {device_id} disconnected")
    except Exception as e:
        logger.error(f"WebSocket error (user watching device {device_id}): {e}")
        await manager.disconnect(room, websocket)


@router.websocket("/ws/geofence/{device_id}")
async def websocket_geofence_alerts(
    websocket: WebSocket,
    device_id: int,
    token: str = Query(None)
):
    """
    WebSocket endpoint for geofence breach alerts.
    Clients subscribe here to receive real-time geofence breach notifications.
    """
    if not token:
        await websocket.close(code=1008, reason="Missing auth token")
        return

    db_conn = connect(dsn=os.getenv("DATABASE_URI"))
    try:
        user = get_user_by_access_token(db_conn, token)
        if user is None:
            await websocket.close(code=1008, reason="Invalid user token")
            return
        user_ids_with_access = get_user_ids_for_device(db_conn, device_id)
        if user.user_id not in user_ids_with_access:
            await websocket.close(code=1008, reason="No access to this device")
            return
    finally:
        db_conn.close()

    room = f"geofence_{device_id}"
    await manager.connect(room, websocket, {"device_id": device_id, "type": "geofence_alert", "user_id": user.user_id})

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "ping":
                await websocket.send_json({
                    "type": "pong",
                    "timestamp": int(time.time() * 1000)
                })

    except WebSocketDisconnect:
        await manager.disconnect(room, websocket)
    except Exception as e:
        logger.error(f"WebSocket error (geofence alerts device {device_id}): {e}")
        await manager.disconnect(room, websocket)


# Helper functions to call from other endpoints

async def broadcast_location_update(device_id: int, location_data: dict) -> int:
    """
    Called from device_data_endpoints when new GPS data is received.
    Broadcasts to all users watching this device.
    """
    message = {
        "type": "location_update",
        "device_id": device_id,
        "data": location_data,
        "timestamp": int(time.time() * 1000)
    }
    room = f"user_device_{device_id}"
    count = await manager.broadcast_to_room(room, message)
    if count > 0:
        logger.debug(f"Location update broadcasted to {count} users for device {device_id}")
    return count


async def broadcast_geofence_breach(device_id: int, geofence_id: int, breach_data: dict) -> int:
    """
    Called from notifications when a geofence breach is detected.
    Broadcasts to all subscribers of this device's geofence alerts.
    """
    message = {
        "type": "geofence_breach",
        "device_id": device_id,
        "geofence_id": geofence_id,
        "data": breach_data,
        "timestamp": int(time.time() * 1000)
    }
    room = f"geofence_{device_id}"
    count = await manager.broadcast_to_room(room, message)
    if count > 0:
        logger.info(f"Geofence breach alert broadcasted to {count} subscribers for device {device_id}")
    return count


async def broadcast_device_control_response(device_id: int, control_data: dict) -> int:
    """
    Called when app/user updates device controls (e.g. kill switch).
    Broadcasts to the device first (for reliable actuation), then to users (UI sync).
    Optionally sends a second copy to the device after a short delay to improve delivery on flaky links.
    """
    # Flatten control fields so both web clients and firmware can consume them easily.
    message: dict = {
        "type": "device_control_response",
        "device_id": device_id,
        "timestamp": int(time.time() * 1000),
        "data": control_data,
    }
    for key in ("control_1", "control_2", "control_3", "control_4", "control_version", "controls_updated_at"):
        if key in control_data:
            message[key] = control_data[key]
    device_room = f"device_{device_id}"
    user_room = f"user_device_{device_id}"
    # Send to device first so the tracker gets the update with priority
    n_device = await manager.broadcast_to_room(device_room, message)
    n_users = await manager.broadcast_to_room(user_room, message)
    # Optional duplicate send to device after a short delay (helps on lossy connections)
    duplicate_delay_ms = int(os.getenv("CONTROL_DUPLICATE_SEND_MS", "0"))
    if duplicate_delay_ms > 0 and n_device > 0:
        await asyncio.sleep(duplicate_delay_ms / 1000.0)
        await manager.broadcast_to_room(device_room, message)
    logger.info(
        "device_control_response broadcast device_id=%s n_users=%s n_device=%s",
        device_id, n_users, n_device,
    )
    return n_users + n_device


@router.get("/ws/stats/{device_id}")
async def get_ws_stats(device_id: int):
    """Get connection statistics for a device's WebSocket rooms."""
    return {
        "device_id": device_id,
        "device_connections": manager.get_room_stats(f"device_{device_id}"),
        "user_listeners": manager.get_room_stats(f"user_device_{device_id}"),
        "geofence_subscribers": manager.get_room_stats(f"geofence_{device_id}"),
    }
