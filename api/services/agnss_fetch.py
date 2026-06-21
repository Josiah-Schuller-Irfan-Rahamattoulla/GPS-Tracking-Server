"""Fetch A-GNSS assistance bytes (nRF Cloud with SUPL fallback)."""

from __future__ import annotations

import logging
import os

import httpx

from api.agnss.cache_store import get_agnss_cache
from api.agnss.supl_client import get_supl_assistance_data
from api.endpoints.agnss_endpoints import auth_bearer_token, build_location_url

logger = logging.getLogger(__name__)


def _parse_content_range(header_value: str | None) -> int | None:
    if not header_value:
        return None
    try:
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


async def fetch_agnss_bytes(
    device_id: int,
    *,
    lat: float | None = None,
    lon: float | None = None,
    mcc: int | None = None,
    mnc: int | None = None,
    tac: int | None = None,
    eci: int | None = None,
) -> tuple[bytes | None, str | None]:
    """
    Return (binary_blob, source_name) or (None, None) when unavailable.
    """
    agnss_data: bytes | None = None
    source: str | None = None
    agnss_provider = os.getenv("AGNSS_PROVIDER", "").strip().upper()

    def _provider_allows(provider: str) -> bool:
        return (not agnss_provider) or agnss_provider == provider

    if _provider_allows("NRF_CLOUD"):
        nrf_cloud_api_key = auth_bearer_token()
        if nrf_cloud_api_key:
            try:
                logger.info("A-GNSS nRF Cloud device_id=%s", device_id)
                url = build_location_url("agnss")
                auth_headers = {"Authorization": f"Bearer {nrf_cloud_api_key}"}
                body: dict[str, object] = {}
                have_cell_ids = (
                    mcc is not None and mnc is not None and tac is not None and eci is not None
                )
                if have_cell_ids:
                    body = {
                        "mcc": mcc,
                        "mnc": mnc,
                        "tac": tac,
                        "eci": eci,
                        "filtered": True,
                        "mask": 5,
                        "types": [1, 2, 3, 4, 6, 7, 8, 9],
                    }
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        url,
                        json=body,
                        headers={
                            **auth_headers,
                            "Accept": "application/octet-stream",
                            "Content-Type": "application/json",
                            "Range": "bytes=0-16383",
                        },
                    )
                    if response.status_code in (200, 206):
                        chunks = [response.content]
                        total_received = len(response.content)
                        total_size = _parse_content_range(response.headers.get("Content-Range"))
                        while total_size is not None and total_received < total_size:
                            next_start = total_received
                            next_response = await client.post(
                                url,
                                json=body,
                                headers={
                                    **auth_headers,
                                    "Accept": "application/octet-stream",
                                    "Content-Type": "application/json",
                                    "Range": f"bytes={next_start}-",
                                },
                            )
                            if next_response.status_code not in (200, 206):
                                break
                            chunk = next_response.content
                            if not chunk:
                                break
                            chunks.append(chunk)
                            total_received += len(chunk)
                        agnss_data = b"".join(chunks)
                        source = "nRF Cloud"
                        logger.info("A-GNSS nRF Cloud device_id=%s bytes=%d", device_id, len(agnss_data))
                    else:
                        logger.warning(
                            "nRF Cloud A-GNSS device_id=%s status=%s",
                            device_id,
                            response.status_code,
                        )
            except Exception as exc:
                logger.warning("nRF Cloud A-GNSS device_id=%s err=%s", device_id, exc)

    if not agnss_data and _provider_allows("SUPL"):
        try:
            cache = get_agnss_cache()
            if cache.enabled:
                cached = cache.get()
                if cached:
                    agnss_data = cached
                    source = "SUPL cache"
            if not agnss_data:
                logger.info("A-GNSS SUPL device_id=%s", device_id)
                agnss_data = await get_supl_assistance_data(device_id, lat, lon)
                if agnss_data:
                    source = "SUPL"
                    if cache.enabled:
                        cache.set(agnss_data)
                    logger.info("A-GNSS SUPL device_id=%s bytes=%d", device_id, len(agnss_data))
        except Exception as exc:
            logger.warning("SUPL A-GNSS device_id=%s err=%s", device_id, exc)

    return agnss_data, source
