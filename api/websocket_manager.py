"""
WebSocket real-time GPS tracking server.
Handles live position updates, device status changes, and notifications.
"""

import logging
import json
from typing import Set, Dict, Any, Optional
from datetime import datetime
import threading

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections per user."""
    
    def __init__(self):
        # user_id -> set of socket.io client IDs
        self.active_connections: Dict[int, Set[str]] = {}
        self.lock = threading.RLock()
    
    def add_connection(self, user_id: int, client_id: str) -> None:
        """Register a new WebSocket connection for a user."""
        with self.lock:
            if user_id not in self.active_connections:
                self.active_connections[user_id] = set()
            self.active_connections[user_id].add(client_id)
            logger.info(f"User {user_id} connected (client: {client_id})")
    
    def remove_connection(self, user_id: int, client_id: str) -> None:
        """Unregister a WebSocket connection."""
        with self.lock:
            if user_id in self.active_connections:
                self.active_connections[user_id].discard(client_id)
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]
            logger.info(f"User {user_id} disconnected (client: {client_id})")
    
    def get_user_clients(self, user_id: int) -> Set[str]:
        """Get all client IDs connected for a user."""
        with self.lock:
            return self.active_connections.get(user_id, set()).copy()
    
    def has_active_connection(self, user_id: int) -> bool:
        """Check if user has any active connections."""
        with self.lock:
            return user_id in self.active_connections and len(self.active_connections[user_id]) > 0
    
    def get_connected_users(self) -> Set[int]:
        """Get all user IDs with active connections."""
        with self.lock:
            return set(self.active_connections.keys())


# Global connection manager instance
connection_manager = ConnectionManager()


def format_gps_update(
    device_id: int,
    latitude: float,
    longitude: float,
    accuracy: Optional[float] = None,
    speed: Optional[float] = None,
    heading: Optional[float] = None,
    timestamp: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """Format GPS data for WebSocket broadcast."""
    if timestamp is None:
        timestamp = datetime.utcnow().isoformat() + "Z"
    
    return {
        "event": "gps_update",
        "data": {
            "device_id": device_id,
            "latitude": latitude,
            "longitude": longitude,
            "accuracy": accuracy,
            "speed": speed,
            "heading": heading,
            "timestamp": timestamp,
            "server_time": datetime.utcnow().isoformat() + "Z",
        }
    }


def format_device_status(
    device_id: int,
    status: str,  # "connected", "disconnected", "stale"
    last_update: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """Format device status for WebSocket broadcast."""
    return {
        "event": "device_status",
        "data": {
            "device_id": device_id,
            "status": status,
            "last_update": last_update,
            "server_time": datetime.utcnow().isoformat() + "Z",
        }
    }


def format_geofence_breach(
    device_id: int,
    geofence_id: str,
    geofence_name: str,
    breach_type: str,  # "entry", "exit"
    latitude: float,
    longitude: float,
    timestamp: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """Format geofence breach event for WebSocket broadcast."""
    if timestamp is None:
        timestamp = datetime.utcnow().isoformat() + "Z"
    
    return {
        "event": "geofence_breach",
        "data": {
            "device_id": device_id,
            "geofence_id": geofence_id,
            "geofence_name": geofence_name,
            "breach_type": breach_type,
            "latitude": latitude,
            "longitude": longitude,
            "timestamp": timestamp,
            "server_time": datetime.utcnow().isoformat() + "Z",
        }
    }
