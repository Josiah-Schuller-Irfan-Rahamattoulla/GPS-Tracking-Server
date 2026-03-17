"""
Debug endpoints to verify server configuration (e.g. NRF Cloud API key on AWS).
No secrets are exposed; only presence/absence of config is reported.
"""
import os
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class AgnssStatusResponse(BaseModel):
    """Whether A-GNSS / cell location backend is configured."""
    nrf_cloud_api_key_configured: bool


@router.get("/debug/agnss_status", response_model=AgnssStatusResponse)
async def get_agnss_status():
    """
    Report whether NRF_CLOUD_API_KEY is set (for A-GNSS and cell location).
    Does not expose the key value. Use this to verify env on AWS.
    """
    key = os.getenv("NRF_CLOUD_API_KEY")
    return AgnssStatusResponse(nrf_cloud_api_key_configured=bool(key and key.strip()))
