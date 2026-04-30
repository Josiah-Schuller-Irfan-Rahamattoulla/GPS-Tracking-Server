"""
nRF Cloud Location Services client helpers.

Supports the current Memfault Organization Auth Token (OAT) auth + org/project scoped URLs:
  https://api.nrfcloud.com/v1/organizations/{org}/projects/{project}/location/...

For migration/backwards compatibility, this module can also fall back to legacy unscoped
Location Services URLs when only NRF_CLOUD_API_KEY is provided.
"""

from __future__ import annotations

import os


def get_oat() -> str | None:
    token = (os.getenv("NRFCLOUD_OAT") or "").strip()
    return token or None


def get_org_slug() -> str | None:
    slug = (os.getenv("NRFCLOUD_ORG_SLUG") or "").strip()
    return slug or None


def get_project_slug() -> str | None:
    slug = (os.getenv("NRFCLOUD_PROJECT_SLUG") or "").strip()
    return slug or None


def get_legacy_api_key() -> str | None:
    """Legacy team API key / service token env var used by older endpoints."""
    token = (os.getenv("NRF_CLOUD_API_KEY") or "").strip()
    return token or None


def location_base_url() -> str:
    """
    Return the base URL for Location Services.

    - Preferred: org/project-scoped base (requires NRFCLOUD_OAT + slugs)
    - Fallback: legacy base (requires NRF_CLOUD_API_KEY)
    """
    oat = get_oat()
    org = get_org_slug()
    project = get_project_slug()

    if oat and org and project:
        return f"https://api.nrfcloud.com/v1/organizations/{org}/projects/{project}/location"

    # Legacy (deprecated) base; kept for compatibility during migration.
    return "https://api.nrfcloud.com/v1/location"


def auth_bearer_token() -> str | None:
    """
    Return the bearer token to use for nRF Cloud Location Services.

    Prefers OAT if configured; falls back to legacy NRF_CLOUD_API_KEY.
    """
    return get_oat() or get_legacy_api_key()


def build_location_url(path: str) -> str:
    """
    Build a full Location Services URL, where `path` is like "agnss" or "cell".
    """
    path = path.lstrip("/")
    return f"{location_base_url().rstrip('/')}/{path}"

