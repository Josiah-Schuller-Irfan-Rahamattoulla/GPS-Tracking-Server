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

# In-memory cache for evaluation token
_evaluation_token = None
_evaluation_token_expiry = None

logger = logging.getLogger(__name__)

router = APIRouter()


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
    async def get_evaluation_token():
        global _evaluation_token, _evaluation_token_expiry
        if _evaluation_token and _evaluation_token_expiry:
            # Check expiry (buffer 60s)
            import time, jwt
            try:
                payload = jwt.decode(_evaluation_token, options={"verify_signature": False})
                if payload.get("exp", 0) > int(time.time()) + 60:
                    return _evaluation_token
            except Exception:
                pass
        # Fetch new token
        url = "https://api.nrfcloud.com/v1/account/service-evaluation-token"
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url)
            if resp.status_code == 200:
                token = resp.json().get("token")
                _evaluation_token = token
                # Parse expiry
                try:
                    import jwt
                    payload = jwt.decode(token, options={"verify_signature": False})
                    _evaluation_token_expiry = payload.get("exp")
                except Exception:
                    _evaluation_token_expiry = None
                return token
            else:
                raise HTTPException(status_code=500, detail="Failed to fetch nRF Cloud evaluation token")

    async def request_agnss_from_nrf_cloud(
        api_key: Optional[str] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        accuracy: Optional[int] = None
    ) -> bytes:
        try:
            # Use provided API key, or fetch evaluation token if missing/invalid
            key = api_key or os.getenv("NRF_CLOUD_API_KEY")
            if not key or key.strip() == "":
                key = await get_evaluation_token()
            async with httpx.AsyncClient(timeout=10.0) as client:
                url = "https://api.nrfcloud.com/v1/agnss/latest"
                params = {}
                if lat is not None and lon is not None:
                    params["lat"] = lat
                    params["lon"] = lon
                    if accuracy:
                        params["accuracy"] = accuracy
                    logger.info(f"A-GNSS: Using position hint lat={lat:.6f} lon={lon:.6f} accuracy={accuracy}m")
                else:
                    logger.info("A-GNSS: No position hint, requesting default ephemeris")
                headers = {"Authorization": f"Bearer {key}"}
                logger.debug(f"Requesting A-GNSS from nRF Cloud with params: {params}")
                response = await client.get(url, params=params, headers=headers)
                logger.info(f"A-GNSS nRF Cloud response status: {response.status_code}")
                logger.info(f"A-GNSS nRF Cloud response headers: {dict(response.headers)}")
                if response.status_code == 200:
                    logger.info(f"A-GNSS data received: {len(response.content)} bytes")
                    logger.info(f"A-GNSS data (first 32 bytes): {response.content[:32].hex()}")
                    return response.content
                elif response.status_code == 401:
                    # Try fetching a new evaluation token and retry once
                    logger.warning("A-GNSS: API key invalid, attempting to fetch evaluation token...")
                    key = await get_evaluation_token()
                    headers = {"Authorization": f"Bearer {key}"}
                    response = await client.get(url, params=params, headers=headers)
                    logger.info(f"A-GNSS nRF Cloud response status (retry): {response.status_code}")
                    if response.status_code == 200:
                        logger.info(f"A-GNSS data received: {len(response.content)} bytes (retry)")
                        logger.info(f"A-GNSS data (first 32 bytes): {response.content[:32].hex()} (retry)")
                        return response.content
                    raise HTTPException(status_code=401, detail="A-GNSS: Invalid nRF Cloud API key (after retry)")
                elif response.status_code == 429:
                    raise HTTPException(status_code=429, detail="A-GNSS: Rate limit exceeded")
                else:
                    error_msg = f"A-GNSS: nRF Cloud returned {response.status_code}: {response.text}"
                    logger.warning(error_msg)
                    raise HTTPException(status_code=response.status_code, detail=error_msg)
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="A-GNSS: nRF Cloud request timeout")
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
