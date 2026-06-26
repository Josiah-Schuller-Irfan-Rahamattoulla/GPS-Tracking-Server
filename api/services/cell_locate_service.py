"""
Resolve cell tower measurements to lat/lon (shared by HTTP and MQTT).
"""

from __future__ import annotations

import logging
import os
from typing import List

import httpx

from api.endpoints.cell_location import (
    CellInfo,
    CellLocationResponse,
    get_google_location,
    get_here_location,
    get_nrf_cloud_location,
)
from api.nrfcloud_location import auth_bearer_token

logger = logging.getLogger(__name__)


class CellLocateUnavailable(Exception):
    """No provider could resolve the cell measurement."""


async def resolve_cell_location(cells: List[CellInfo]) -> CellLocationResponse:
    """Query configured provider(s) for an estimated position."""
    if not cells:
        raise ValueError("At least one cell required")

    provider = os.getenv("CELL_LOCATION_PROVIDER", "nrf_cloud").strip().lower()
    if provider == "auto":
        provider_order = ["nrf_cloud", "google", "here"]
    else:
        provider_order = [provider]

    errors: list[str] = []

    for candidate in provider_order:
        try:
            if candidate == "nrf_cloud":
                api_key = auth_bearer_token()
                if not api_key:
                    errors.append(
                        "NRFCLOUD_OAT/NRFCLOUD_ORG_SLUG/NRFCLOUD_PROJECT_SLUG not configured "
                        "(or legacy NRF_CLOUD_API_KEY missing)"
                    )
                    continue
                return await get_nrf_cloud_location(cells, api_key)

            if candidate == "google":
                api_key = os.getenv("GOOGLE_GEOLOCATION_API_KEY")
                if not api_key:
                    errors.append("GOOGLE_GEOLOCATION_API_KEY not configured")
                    continue
                return await get_google_location(cells, api_key)

            if candidate == "here":
                api_key = os.getenv("HERE_API_KEY")
                if not api_key:
                    errors.append("HERE_API_KEY not configured")
                    continue
                return await get_here_location(cells, api_key)

            errors.append(f"Unknown CELL_LOCATION_PROVIDER: {candidate}")

        except httpx.HTTPStatusError as exc:
            logger.error(
                "Cell location provider error: %s - %s",
                exc.response.status_code,
                exc.response.text,
            )
            errors.append(f"{candidate} HTTP {exc.response.status_code}")
        except httpx.RequestError as exc:
            logger.error("Cell location request error: %s", str(exc))
            errors.append(f"{candidate} request failed")
        except Exception as exc:
            logger.error("Unexpected error in cell location: %s", str(exc))
            errors.append(f"{candidate} unexpected error")

    detail = "Cell location unavailable"
    if errors:
        detail = f"Cell location unavailable: {', '.join(errors)}"
    raise CellLocateUnavailable(detail)


def parse_cell_infos(raw_cells: list) -> List[CellInfo]:
    """Build CellInfo models from MQTT/JSON cell dicts."""
    if not isinstance(raw_cells, list) or not raw_cells:
        raise ValueError("cells must be a non-empty array")

    out: List[CellInfo] = []
    for item in raw_cells:
        if not isinstance(item, dict):
            raise ValueError("each cell must be an object")
        out.append(
            CellInfo(
                cellId=int(item["cellId"]),
                mcc=int(item["mcc"]),
                mnc=int(item["mnc"]),
                lac=int(item.get("lac", item.get("tac", 0))),
                signal=int(item.get("signal", item.get("rsrp", -120))),
                tac=int(item["tac"]) if item.get("tac") is not None else None,
            )
        )
    return out
