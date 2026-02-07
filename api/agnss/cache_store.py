import json
import logging
import os
import time
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class AgnssCache:
    path: str
    ttl_sec: int

    @property
    def enabled(self) -> bool:
        return self.ttl_sec > 0

    @property
    def meta_path(self) -> str:
        return self.path + ".json"

    def _read_meta(self) -> dict | None:
        try:
            with open(self.meta_path, "r", encoding="utf-8") as handle:
                return json.load(handle)
        except FileNotFoundError:
            return None
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("A-GNSS cache meta read failed: %s", exc)
            return None

    def _write_meta(self, size: int) -> None:
        data = {
            "timestamp": time.time(),
            "size": size,
        }
        tmp_path = self.meta_path + ".tmp"
        try:
            with open(tmp_path, "w", encoding="utf-8") as handle:
                json.dump(data, handle)
            os.replace(tmp_path, self.meta_path)
        except OSError as exc:
            logger.warning("A-GNSS cache meta write failed: %s", exc)

    def get(self) -> bytes | None:
        if not self.enabled:
            return None

        meta = self._read_meta()
        if not meta or "timestamp" not in meta:
            return None

        age = time.time() - float(meta["timestamp"])
        if age > self.ttl_sec:
            return None

        try:
            with open(self.path, "rb") as handle:
                return handle.read()
        except FileNotFoundError:
            return None
        except OSError as exc:
            logger.warning("A-GNSS cache read failed: %s", exc)
            return None

    def set(self, data: bytes) -> None:
        if not self.enabled:
            return

        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        tmp_path = self.path + ".tmp"
        try:
            with open(tmp_path, "wb") as handle:
                handle.write(data)
            os.replace(tmp_path, self.path)
            self._write_meta(len(data))
        except OSError as exc:
            logger.warning("A-GNSS cache write failed: %s", exc)


def get_agnss_cache() -> AgnssCache:
    path = os.getenv("AGNSS_CACHE_PATH", "/app/agnss_cache.bin")
    ttl_raw = os.getenv("AGNSS_CACHE_TTL_SEC", "7200")
    try:
        ttl_sec = int(ttl_raw)
    except ValueError:
        ttl_sec = 7200
    return AgnssCache(path=path, ttl_sec=ttl_sec)
