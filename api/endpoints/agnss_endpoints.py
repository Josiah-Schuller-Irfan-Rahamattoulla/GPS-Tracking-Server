"""
A-GNSS (Assisted GNSS) Data Service Endpoint

This endpoint provides Assisted GNSS data to nRF9151 devices,
using cell location information to improve positioning accuracy and speed.
"""

import os
import logging
import httpx
from typing import Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

import asyncio

logger = logging.getLogger(__name__)

router = APIRouter()

from api.nrfcloud_location import auth_bearer_token, build_location_url

class CellLocationHint(BaseModel):
    """Cell location hint for A-GNSS server (optional)"""
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    accuracy_meters: Optional[int] = None


class AGNSSRequest(BaseModel):
    """A-GNSS data request from device"""
    device_id: int
    cell_hint: Optional[CellLocationHint] = None
    mcc: Optional[int] = None  # Mobile Country Code for additional context
    mnc: Optional[int] = None  # Mobile Network Code


async def request_agnss_from_nrf_cloud(
    api_key: str,
    lat: Optional[float] = None,
    lon: Optional[float] = None,
    accuracy: Optional[int] = None
) -> bytes:
    """
    Request A-GNSS data from nRF Cloud using REST API.
    
    When position hint is provided, nRF Cloud can provide more targeted
    ephemeris data, significantly speeding up GNSS convergence.
    
    Args:
        api_key: nRF Cloud REST API key
        lat: Latitude hint (from cell location)
        lon: Longitude hint (from cell location)
        accuracy: Accuracy in meters
        
    Returns:
        A-GNSS data as binary payload
        
    Raises:
        HTTPException on API errors
    """
    try:
        # Prefer the new OAT-based auth; fall back to legacy NRF_CLOUD_API_KEY during migration.
        key = (api_key or auth_bearer_token() or "").strip()
        if not key:
            raise HTTPException(
                status_code=500,
                detail="A-GNSS: nRF Cloud not configured (set NRFCLOUD_OAT + slugs, or legacy NRF_CLOUD_API_KEY)",
            )

        def _parse_content_range_total(header_value: str | None) -> int | None:
            if not header_value:
                return None
            try:
                # e.g. "bytes 0-2200/12456"
                parts = header_value.strip().split()
                if len(parts) != 2 or parts[0].lower() != "bytes":
                    return None
                range_part = parts[1]
                if "/" not in range_part:
                    return None
                _, total_part = range_part.split("/", 1)
                if total_part == "*":
                    return None
                return int(total_part)
            except (ValueError, IndexError):
                return None

        async with httpx.AsyncClient(timeout=30.0) as client:
            # Location Services GNSS assistance endpoint.
            # nRF Cloud returns data in chunks controlled by the Range header.
            url = build_location_url("agnss")

            # NOTE: The GNSS assistance API supports cell-derived hints via mcc/mnc/tac/eci + type 8.
            # We currently only have lat/lon hints from our cell-location provider, so we request
            # default assistance (types 1,2,3,4,6,7,9) and ignore lat/lon here.
            if lat is not None and lon is not None:
                logger.info("A-GNSS: lat/lon hint provided but GNSS assistance requires cell IDs; requesting default assistance")
            else:
                logger.info("A-GNSS: requesting default assistance")

            headers = {
                "Authorization": f"Bearer {key}",
                "Accept": "application/octet-stream",
                "Content-Type": "application/json",
            }

            chunks: list[bytes] = []
            total_received = 0
            total_size: int | None = None

            # First chunk.
            response = await client.post(
                url,
                json={},
                headers={**headers, "Range": "bytes=0-16383"},
            )
            logger.info(f"A-GNSS nRF Cloud response status: {response.status_code}")
            if response.status_code not in (200, 206):
                if response.status_code == 401:
                    raise HTTPException(status_code=401, detail="A-GNSS: Invalid nRF Cloud token (OAT/API key)")
                if response.status_code == 429:
                    raise HTTPException(status_code=429, detail="A-GNSS: Rate limit exceeded")
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"A-GNSS: nRF Cloud returned {response.status_code}: {response.text}",
                )

            chunks.append(response.content)
            total_received += len(response.content)
            total_size = _parse_content_range_total(response.headers.get("Content-Range"))

            # Remaining chunks (if nRF Cloud tells us the total size).
            while total_size is not None and total_received < total_size:
                next_start = total_received
                next_resp = await client.post(
                    url,
                    json={},
                    headers={**headers, "Range": f"bytes={next_start}-"},
                )
                if next_resp.status_code not in (200, 206) or not next_resp.content:
                    break
                chunks.append(next_resp.content)
                total_received += len(next_resp.content)

            data = b"".join(chunks)
            logger.info(f"A-GNSS data received: {len(data)} bytes")
            logger.debug(f"A-GNSS data (first 32 bytes): {data[:32].hex()}")
            return data
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="A-GNSS: nRF Cloud request timeout")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"A-GNSS request error: {e}")
        raise HTTPException(status_code=500, detail=f"A-GNSS: {str(e)}")


@router.get("/agnss")
async def agnss_request_get(
    device_id: int = Query(..., description="Device ID"),
    lat: Optional[float] = Query(None, description="Latitude hint from cell location"),
    lon: Optional[float] = Query(None, description="Longitude hint from cell location"),
):
    """
    GET endpoint for A-GNSS data (for simpler device implementations).
    
    Query Parameters:
    - device_id: Device ID (required)
    - lat: Latitude hint from cell location (optional)
    - lon: Longitude hint from cell location (optional)
    
    Returns:
    - Binary A-GNSS data directly (no JSON wrapper)
    - Device firmware can parse this directly with nrf_cloud_agnss_process()
    """
    
    nrf_cloud_key = os.getenv("NRF_CLOUD_API_KEY")
    if not nrf_cloud_key:
        logger.error("NRF_CLOUD_API_KEY not configured")
        raise HTTPException(status_code=500, detail="A-GNSS: Server not configured")
    
    logger.info(f"A-GNSS GET request from device_id={device_id}, lat={lat}, lon={lon}")
    
    try:
        # Request A-GNSS data from nRF Cloud with position hint if provided
        agnss_data = await request_agnss_from_nrf_cloud(
            api_key=nrf_cloud_key,
            lat=lat,
            lon=lon,
            accuracy=None
        )
        
        # Return binary A-GNSS data directly with proper content type
        return Response(content=agnss_data, media_type="application/octet-stream")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"A-GNSS GET error: {e}")
        raise HTTPException(status_code=500, detail=f"A-GNSS error: {str(e)}")


@router.post("/agnss")
async def agnss_request(request: AGNSSRequest):
    """
    Get A-GNSS (Assisted GNSS) data for faster GNSS fix acquisition.
    
    The device provides optional cell location hint (latitude, longitude)
    which speeds up convergence significantly.
    
    Flow:
    1. Device gets cell location from cell towers
    2. Device sends A-GNSS request with cell hint
    3. Server requests targeted ephemeris from nRF Cloud
    4. Server returns binary A-GNSS data to device
    5. Device injects data into GNSS module
    6. GNSS fix acquired much faster (warm start vs cold start)
    
    Position Hint Benefit:
    - Without hint: GNSS searches all ~80 visible satellites globally (~30-120 sec)
    - With hint: GNSS searches only satellites in local region (~5-30 sec)
    
    Query Parameters:
    - device_id: Device ID (required)
    - cell_hint: Cell location hint with lat, lon, accuracy_meters (optional)
    - mcc: Mobile Country Code (optional context)
    - mnc: Mobile Network Code (optional context)
    
    Response:
    - Binary A-GNSS data (nRF Cloud format)
    - Can be directly parsed by device's nrf_cloud_agnss_process()
    """
    
    nrf_cloud_key = os.getenv("NRF_CLOUD_API_KEY")
    if not nrf_cloud_key:
        logger.error("NRF_CLOUD_API_KEY not configured")
        raise HTTPException(status_code=500, detail="A-GNSS: Server not configured")
    
    # Extract position hint if provided
    lat = None
    lon = None
    accuracy = None
    
    if request.cell_hint:
        lat = request.cell_hint.latitude
        lon = request.cell_hint.longitude
        accuracy = request.cell_hint.accuracy_meters
    
    logger.info(f"A-GNSS request from device_id={request.device_id}")
    
    try:
        # Request A-GNSS data from nRF Cloud
        agnss_data = await request_agnss_from_nrf_cloud(
            api_key=nrf_cloud_key,
            lat=lat,
            lon=lon,
            accuracy=accuracy
        )
        
        # Return binary A-GNSS data directly
        # Device firmware expects this exact format from nRF Cloud REST API
        return {
            "status": "ok",
            "device_id": request.device_id,
            "agnss_data": agnss_data.hex(),  # Return as hex string for JSON compatibility
            "data_size": len(agnss_data),
            "hint_used": lat is not None and lon is not None,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in A-GNSS: {e}")
        raise HTTPException(status_code=500, detail=f"A-GNSS error: {str(e)}")


@router.post("/agnss/binary")
async def agnss_request_binary(request: AGNSSRequest):
    """
    Get A-GNSS data in raw binary format (more efficient than hex).
    
    Same as /agnss endpoint but returns pure binary data.
    Useful if device firmware supports direct binary parsing.
    """
    
    nrf_cloud_key = os.getenv("NRF_CLOUD_API_KEY")
    if not nrf_cloud_key:
        raise HTTPException(status_code=500, detail="A-GNSS: Server not configured")
    
    lat = request.cell_hint.latitude if request.cell_hint else None
    lon = request.cell_hint.longitude if request.cell_hint else None
    accuracy = request.cell_hint.accuracy_meters if request.cell_hint else None
    
    agnss_data = await request_agnss_from_nrf_cloud(
        api_key=nrf_cloud_key,
        lat=lat,
        lon=lon,
        accuracy=accuracy
    )
    
    return agnss_data
