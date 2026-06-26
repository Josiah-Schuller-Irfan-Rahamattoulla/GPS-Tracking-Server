"""
Cell-based location services endpoint.
Provides instant positioning using cellular tower information.
Supports nRF Cloud, HERE, and Google positioning APIs.
"""
import logging
import os
from typing import List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Header
import httpx

logger = logging.getLogger(__name__)
router = APIRouter()

from api.nrfcloud_location import auth_bearer_token, build_location_url


class CellInfo(BaseModel):
    """Single cell tower information"""
    cellId: int
    mcc: int  # Mobile Country Code (e.g., 234 for UK)
    mnc: int  # Mobile Network Code (e.g., 10 for O2)
    lac: int  # Location Area Code
    signal: int  # Signal strength in dBm (-50 to -120)
    tac: Optional[int] = None  # Tracking Area Code (LTE)
    

class CellLocationRequest(BaseModel):
    """Request body for cell location"""
    cells: List[CellInfo]
    device_id: Optional[int] = None


class CellLocationResponse(BaseModel):
    """Response with estimated position"""
    latitude: float
    longitude: float
    accuracy: float  # Accuracy radius in meters (can be fractional)
    source: str  # "nrf_cloud", "here", or "google"


async def get_nrf_cloud_location(cells: List[CellInfo], api_key: str) -> CellLocationResponse:
    """
    Use nRF Cloud Location Services for cell-based positioning.
    Docs: https://api.nrfcloud.com/v1#tag/Location-Services
    """
    # Convert to nRF Cloud format
    lte_cells = []
    for cell in cells:
        lte_cells.append({
            "mcc": cell.mcc,
            "mnc": cell.mnc,
            "tac": cell.tac or cell.lac,  # Use TAC if available, fallback to LAC
            "eci": cell.cellId,  # E-UTRAN Cell Identifier
            "rsrp": cell.signal,  # RSRP (Reference Signal Received Power)
        })
    
    # nRF Cloud Multi-Cell Location request
    payload = {
        "lte": lte_cells
    }
    
    url = build_location_url("cell")
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
    
    # nRF Cloud response format:
    # {
    #   "lat": 51.5074,
    #   "lon": -0.1278,
    #   "uncertainty": 500
    # }
    
    return CellLocationResponse(
        latitude=data["lat"],
        longitude=data["lon"],
        accuracy=data.get("uncertainty", 1000),
        source="nrf_cloud"
    )


async def get_here_location(cells: List[CellInfo], api_key: str) -> CellLocationResponse:
    """
    Use HERE Positioning API for cell-based location.
    Docs: https://developer.here.com/documentation/positioning
    """
    # Convert to HERE format
    lte_cells = []
    for cell in cells:
        lte_cells.append({
            "mcc": cell.mcc,
            "mnc": cell.mnc,
            "cid": cell.cellId,
            "tac": cell.tac or cell.lac,
            "rssi": cell.signal
        })
    
    payload = {
        "lte": lte_cells
    }
    
    url = "https://positioning.hereapi.com/v2/position"
    params = {"apiKey": api_key}
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(url, json=payload, params=params)
        response.raise_for_status()
        data = response.json()
    
    location = data["location"]
    return CellLocationResponse(
        latitude=location["lat"],
        longitude=location["lng"],
        accuracy=location.get("accuracy", 1000),
        source="here"
    )


async def get_google_location(cells: List[CellInfo], api_key: str) -> CellLocationResponse:
    """
    Use Google Geolocation API for cell-based positioning.
    Docs: https://developers.google.com/maps/documentation/geolocation
    """
    # Convert to Google format
    cell_towers = []
    for cell in cells:
        cell_towers.append({
            "cellId": cell.cellId,
            "locationAreaCode": cell.lac,
            "mobileCountryCode": cell.mcc,
            "mobileNetworkCode": cell.mnc,
            "signalStrength": cell.signal
        })
    
    payload = {
        "cellTowers": cell_towers,
        "considerIp": False
    }
    
    url = f"https://www.googleapis.com/geolocation/v1/geolocate?key={api_key}"
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
    
    return CellLocationResponse(
        latitude=data["location"]["lat"],
        longitude=data["location"]["lng"],
        accuracy=data.get("accuracy", 1000),
        source="google"
    )


@router.post("/cell_location", response_model=CellLocationResponse)
async def get_cell_location(
    request: CellLocationRequest,
    access_token: str = Header(None, alias="Access-Token")
):
    """
    Get estimated position from cellular tower information.
    
    This provides instant positioning without GPS, using cell tower triangulation.
    Accuracy: 100-2000 meters depending on cell density.
    
    Use cases:
    - Instant position on device boot (before GPS fix)
    - Indoor tracking where GPS unavailable
    - Low-power tracking mode
    - Provide lat/lon for A-GNSS request
    
    Request body:
    {
      "cells": [{
        "cellId": 12345,
        "mcc": 234,
        "mnc": 10,
        "lac": 5432,
        "signal": -85
      }],
      "device_id": 100
    }
    
    Returns estimated lat/lon with accuracy radius in meters.
    """
    from api.services.cell_locate_service import CellLocateUnavailable, resolve_cell_location

    if not request.cells:
        raise HTTPException(status_code=400, detail="At least one cell required")

    try:
        return await resolve_cell_location(request.cells)
    except CellLocateUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
