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
    nrfcloud_oat_configured: bool
    nrfcloud_org_configured: bool
    nrfcloud_project_configured: bool
    legacy_nrf_cloud_api_key_configured: bool


@router.get("/debug/agnss_status", response_model=AgnssStatusResponse)
async def get_agnss_status():
    """
    Report whether nRF Cloud Location Services auth is configured.
    Does not expose any secret values. Use this to verify env on AWS.
    """
    oat = os.getenv("NRFCLOUD_OAT")
    org = os.getenv("NRFCLOUD_ORG_SLUG")
    project = os.getenv("NRFCLOUD_PROJECT_SLUG")
    legacy = os.getenv("NRF_CLOUD_API_KEY")
    return AgnssStatusResponse(
        nrfcloud_oat_configured=bool(oat and oat.strip()),
        nrfcloud_org_configured=bool(org and org.strip()),
        nrfcloud_project_configured=bool(project and project.strip()),
        legacy_nrf_cloud_api_key_configured=bool(legacy and legacy.strip()),
    )
