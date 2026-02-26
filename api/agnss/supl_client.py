"""
SUPL (Secure User Plane Location) client for fetching A-GNSS assistance data.
Connects to free SUPL servers (Google, Nokia) to get satellite ephemeris/almanac.
"""

import logging
import struct
from typing import Optional
import socket
import time

logger = logging.getLogger(__name__)

# SUPL Protocol constants
SUPL_VERSION = 0x020000  # Version 2.0.0
SET_ID_TYPE_MSISDN = 0   # Mobile Station ISDN
SET_ID_TYPE_IMEI = 1     # International Mobile Equipment Identity
SET_ID_TYPE_IMSI = 2     # International Mobile Subscriber Identity

# SUPL Message types
ULPD_MSG_TYPE_SUPLSTART = 0
ULPD_MSG_TYPE_SUPLRESPONSE = 1
ULPD_MSG_TYPE_SUPLLOCATIONREQUEST = 2
ULPD_MSG_TYPE_SUPLLOCATIONRESPONSE = 3
ULPD_MSG_TYPE_SUPLAUTHREQUEST = 4
ULPD_MSG_TYPE_SUPLAUTHRESPONSE = 5
ULPD_MSG_TYPE_SUPLPOSINIT = 6
ULPD_MSG_TYPE_SUPLPOSEND = 7
ULPD_MSG_TYPE_SUPLEND = 8

# Assistance Data types
ASSISTANCE_DATA_TYPE_EPHEMERIS = 0
ASSISTANCE_DATA_TYPE_ALMANAC = 1
ASSISTANCE_DATA_TYPE_IONOSPHERE = 3
ASSISTANCE_DATA_TYPE_DGPS = 4


class SUPLClient:
    """Simple SUPL client for fetching A-GNSS data from public SUPL servers."""
    
    # Free SUPL servers (no authentication required)
    # Using Google SUPL with IPv4 address first to bypass DNS issues
    SUPL_SERVERS = [
        ("74.125.68.192", 7276),         # Google SUPL (resolved IPv4)
        ("supl.google.com", 7276),      # Google's SUPL server  
        ("supl.nokia.com", 7275),        # Nokia's SUPL server
        ("supl.xse.com", 7275),          # XSE SUPL server
    ]
    
    def __init__(self, device_id: int, timeout: float = 30.0):
        self.device_id = device_id
        self.timeout = timeout
        self.socket = None
        self.server_idx = 0
    
    def _encode_length(self, length: int) -> bytes:
        """Encode SUPL message length (ULP PDU length encoding)."""
        if length < 128:
            return bytes([length])
        elif length < 16384:
            # 2-byte length: first byte has high bit set
            return bytes([(length >> 8) | 0x80, length & 0xFF])
        else:
            raise ValueError(f"Message too large: {length}")
    
    def _create_suplstart(self, latitude: Optional[float] = None, 
                         longitude: Optional[float] = None) -> bytes:
        """
        Create a SUPL START message.
        Minimal implementation - sends device ID and optional location.
        """
        msg = bytearray()
        
        # ULP PDU message type (SUPLSTART = 0)
        msg.append(0x00)
        
        # Session ID (simple: device_id as 4 bytes)
        msg.extend(struct.pack(">I", self.device_id % (2**32)))
        
        # Set ID type (IMEI)
        set_id = bytearray()
        set_id.append(SET_ID_TYPE_IMEI)
        # IMEI as string (use device_id as placeholder)
        imei_str = f"{self.device_id:015d}".encode('ascii')
        set_id.extend(imei_str[:15])  # IMEI is max 15 digits
        msg.extend(set_id)
        
        # Location assistance (optional)
        if latitude is not None and longitude is not None:
            msg.append(0x01)  # Has location
            # Latitude: -90 to +90, encoded as signed int (-2^23 to +2^23)
            lat_encoded = int((latitude + 90) * (2**23) / 180)
            msg.extend(struct.pack(">i", lat_encoded)[:3])  # 3 bytes
            
            # Longitude: -180 to +180, encoded as signed int (-2^24 to +2^24)
            lon_encoded = int((longitude + 180) * (2**24) / 360)
            msg.extend(struct.pack(">i", lon_encoded)[:3])  # 3 bytes
        else:
            msg.append(0x00)  # No location
        
        logger.debug(f"SUPL START message: {msg.hex()}")
        return bytes(msg)
    
    def fetch_assistance_data(self, latitude: Optional[float] = None,
                                   longitude: Optional[float] = None) -> Optional[bytes]:
        """
        Fetch A-GNSS assistance data from SUPL server.
        Returns raw binary assistance data (ephemeris/almanac) or None on failure.
        """
        
        for attempt, (host, port) in enumerate(self.SUPL_SERVERS):
            sock = None
            assistance_data = bytearray()
            try:
                logger.info(f"Attempting SUPL connection to {host}:{port} (attempt {attempt + 1})")
                
                # Resolve hostname and try all addresses (IPv4 and IPv6)
                try:
                    addr_info = socket.getaddrinfo(host, port, socket.AF_UNSPEC, socket.SOCK_STREAM)
                except socket.gaierror as dns_err:
                    logger.warning(f"SUPL connection failed to {host}:{port}: {dns_err}")
                    continue
                
                for family, socktype, proto, canonname, sockaddr in addr_info:
                    try:
                        # Create socket
                        sock = socket.socket(family, socktype, proto)
                        sock.settimeout(self.timeout)
                        
                        # Connect
                        sock.connect(sockaddr)
                        logger.info(f"Connected to {host}:{port} via {sockaddr}")
                        break  # Connection successful
                    except (socket.error, OSError) as conn_err:
                        if sock:
                            sock.close()
                            sock = None
                        logger.debug(f"Connection to {sockaddr} failed: {conn_err}")
                        continue
                
                if not sock:
                    logger.warning(f"SUPL connection failed to {host}:{port}: All addresses failed")
                    continue
                
                # Send SUPL START
                try:
                    start_msg = self._create_suplstart(latitude, longitude)
                    length_header = self._encode_length(len(start_msg))
                    sock.sendall(length_header + start_msg)
                    logger.info(f"Sent SUPL START to {host}:{port} ({len(start_msg)} bytes)")
                except Exception as send_err:
                    logger.warning(f"Failed to send SUPL START to {host}:{port}: {send_err}")
                    if sock:
                        sock.close()
                    continue
                
                # Receive response (try to get assistance data)
                assistance_data = bytearray()
                start_time = time.time()
                
                while time.time() - start_time < self.timeout:
                    try:
                        # Read length header (1-2 bytes)
                        length_bytes = sock.recv(1)
                        if not length_bytes:
                            break
                        
                        msg_len = length_bytes[0]
                        if msg_len & 0x80:  # 2-byte length
                            next_byte = sock.recv(1)
                            if not next_byte:
                                break
                            msg_len = ((length_bytes[0] & 0x7F) << 8) | next_byte[0]
                        
                        # Read message body
                        msg_body = sock.recv(msg_len)
                        if not msg_body:
                            break
                        
                        logger.debug(f"Received SUPL message ({len(msg_body)} bytes): {msg_body[:20].hex()}...")
                        
                        # Parse message type
                        msg_type = msg_body[0] >> 4
                        
                        if msg_type == ULPD_MSG_TYPE_SUPLRESPONSE:
                            # Server acknowledged
                            logger.info("Received SUPL RESPONSE")
                        elif msg_type == ULPD_MSG_TYPE_SUPLLOCATIONREQUEST:
                            # Server requesting location
                            logger.info("Received SUPL LOCATION REQUEST")
                        elif msg_type == ULPD_MSG_TYPE_SUPLEND:
                            # Server ending session
                            logger.info("Received SUPL END")
                            break
                        else:
                            # Accumulate assistance data
                            assistance_data.extend(msg_body)
                            logger.debug(f"Accumulated {len(assistance_data)} bytes of assistance data")
                            
                            # If we got enough data, send END and return
                            if len(assistance_data) > 100:
                                end_msg = bytes([0x80 | ULPD_MSG_TYPE_SUPLEND])  # SUPLEND
                                sock.sendall(self._encode_length(len(end_msg)) + end_msg)
                                break
                    
                    except socket.timeout:
                        logger.debug("Socket timeout while waiting for response")
                        break
                
                if sock:
                    sock.close()
                
                if assistance_data:
                    logger.info(f"Successfully fetched {len(assistance_data)} bytes from SUPL server {host}:{port}")
                    return bytes(assistance_data)
                else:
                    logger.warning(f"No assistance data received from {host}:{port} after successful connection")
            
            except socket.gaierror as e:
                logger.warning(f"SUPL connection failed to {host}:{port}: {e}")
                if sock:
                    sock.close()
                continue
            
            except socket.error as e:
                logger.warning(f"SUPL connection failed to {host}:{port}: {e}")
                if sock:
                    sock.close()
                continue
            
            except Exception as e:
                logger.error(f"SUPL error: {e}")
                if sock:
                    sock.close()
        
        logger.error("All SUPL servers failed")
        return None


async def get_supl_assistance_data(device_id: int, 
                                   latitude: Optional[float] = None,
                                   longitude: Optional[float] = None) -> Optional[bytes]:
    """
    High-level function to fetch SUPL assistance data.
    Returns binary A-GNSS data or None if all servers fail.
    
    For testing/demo purposes, returns sample A-GNSS data if SUPL_DEMO env var is set.
    """
    import os
    import asyncio
    
    # Demo mode: return sample data for testing
    if os.getenv("SUPL_DEMO") == "1":
        logger.info("SUPL DEMO MODE: Returning sample A-GNSS data")
        # Sample A-GNSS binary data (minimal valid ephemeris)
        return bytes([0x0a, 0x50, 0x75, 0x6c, 0x73, 0x61, 0x72]) + b"DEMO_AGNSS_DATA" * 20
    
    client = SUPLClient(device_id)
    # Run blocking socket operations in executor to avoid blocking async event loop
    return await asyncio.to_thread(client.fetch_assistance_data, latitude, longitude)
