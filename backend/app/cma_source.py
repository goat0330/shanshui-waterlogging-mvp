from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import ProxyHandler, Request, build_opener

from .models import (
    MeteorologyNowcastFrame,
    MeteorologySourceHealth,
    MeteorologySourceHealthStatus,
    MeteorologyWarning,
)


@dataclass(frozen=True)
class CmaContextResult:
    warnings: list[MeteorologyWarning]
    frames: list[MeteorologyNowcastFrame]
    source_health: list[MeteorologySourceHealth]
    observed_at: datetime | None


class CmaSourceAdapter:
    """Configurable CMA/12379-compatible metadata seam.

    No endpoint is invented. If URLs are not configured the service remains
    NOT_VERIFIED. When a machine-readable JSON endpoint is supplied locally,
    only warning metadata and georeferenced nowcast metadata are normalized.
    Raw radar pixels are never written into FloodForecast.
    """

    WARNING_SOURCE = "NATIONAL_WEATHER_WARNING"
    NOWCAST_SOURCE = "CMA_RADAR_NOWCAST"

    def __init__(self, warning_url: str | None = None, nowcast_url: str | None = None, timeout_seconds: float = 8.0) -> None:
        self.warning_url = self._url_or_none(warning_url)
        self.nowcast_url = self._url_or_none(nowcast_url)
        self.timeout_seconds = timeout_seconds if timeout_seconds > 0 else 8.0
        self._opener = build_opener(ProxyHandler({}))

    @classmethod
    def from_env(cls) -> "CmaSourceAdapter":
        timeout_raw = os.getenv("CMA_TIMEOUT_SECONDS", "8").strip()
        try:
            timeout = float(timeout_raw)
        except ValueError:
            timeout = 8.0
        return cls(
            warning_url=os.getenv("CMA_WARNING_URL", "").strip() or None,
            nowcast_url=os.getenv("CMA_NOWCAST_URL", "").strip() or None,
            timeout_seconds=timeout,
        )

    def fetch(self, received_at: datetime | None = None) -> CmaContextResult:
        received_at = received_at or datetime.now(timezone.utc)
        warnings, warning_health = self._fetch_warning_domain(received_at)
        frames, nowcast_health = self._fetch_nowcast_domain(received_at)
        observed = [item.issuedAt for item in warnings] + [item.validAt for item in frames]
        return CmaContextResult(
            warnings=warnings,
            frames=frames,
            source_health=[warning_health, nowcast_health],
            observed_at=max(observed) if observed else None,
        )

    def _fetch_warning_domain(self, received_at: datetime) -> tuple[list[MeteorologyWarning], MeteorologySourceHealth]:
        if not self.warning_url:
            return [], self._health(self.WARNING_SOURCE, "WARNING_API_UNCONFIGURED", MeteorologySourceHealthStatus.NOT_VERIFIED, received_at, "Set CMA_WARNING_URL to a verified machine-readable JSON endpoint")
        try:
            payload = self._fetch_json(self.warning_url)
            warnings = self.parse_warnings(payload)
            observed = max((item.issuedAt for item in warnings), default=None)
            return warnings, MeteorologySourceHealth(
                provider=self.WARNING_SOURCE,
                sourceId=self.warning_url,
                status=MeteorologySourceHealthStatus.OK,
                observedAt=observed,
                receivedAt=received_at,
                message=None,
            )
        except Exception as exc:
            return [], self._health(self.WARNING_SOURCE, self.warning_url, MeteorologySourceHealthStatus.UNAVAILABLE, received_at, str(exc))

    def _fetch_nowcast_domain(self, received_at: datetime) -> tuple[list[MeteorologyNowcastFrame], MeteorologySourceHealth]:
        if not self.nowcast_url:
            return [], self._health(self.NOWCAST_SOURCE, "RADAR_NOWCAST_UNCONFIGURED", MeteorologySourceHealthStatus.NOT_VERIFIED, received_at, "Set CMA_NOWCAST_URL to a verified georeferenced metadata JSON endpoint")
        try:
            payload = self._fetch_json(self.nowcast_url)
            frames = self.parse_nowcast(payload)
            observed = max((item.validAt for item in frames), default=None)
            return frames, MeteorologySourceHealth(
                provider=self.NOWCAST_SOURCE,
                sourceId=self.nowcast_url,
                status=MeteorologySourceHealthStatus.OK,
                observedAt=observed,
                receivedAt=received_at,
                message=None,
            )
        except Exception as exc:
            return [], self._health(self.NOWCAST_SOURCE, self.nowcast_url, MeteorologySourceHealthStatus.UNAVAILABLE, received_at, str(exc))

    def _fetch_json(self, url: str) -> Any:
        request = Request(url, headers={"Accept": "application/json", "User-Agent": "ShanshuiWaterloggingMVP/0.1"})
        try:
            with self._opener.open(request, timeout=self.timeout_seconds) as response:
                if response.status != 200:
                    raise RuntimeError(f"HTTP {response.status}")
                raw = response.read()
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            raise RuntimeError(f"fetch failed: {exc}") from exc
        try:
            return json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RuntimeError("invalid JSON") from exc

    @classmethod
    def parse_warnings(cls, payload: Any) -> list[MeteorologyWarning]:
        items = cls._items(payload, "warnings")
        result: list[MeteorologyWarning] = []
        for index, raw in enumerate(items):
            if not isinstance(raw, dict):
                continue
            warning_type = cls._first_text(raw, "type", "event", "warningType", "headline")
            level = cls._first_text(raw, "level", "severity", "warningLevel")
            issued = cls._first_datetime(raw, "issuedAt", "sent", "issueTime", "publishTime")
            if not warning_type or not level or issued is None:
                continue
            source_id = cls._first_text(raw, "sourceId", "identifier", "id") or f"WARNING-{index + 1}"
            result.append(MeteorologyWarning(
                type=warning_type,
                level=level,
                issuedAt=issued,
                expiresAt=cls._first_datetime(raw, "expiresAt", "expires", "expireTime"),
                sourceId=source_id,
                area=cls._first_text(raw, "area", "areaDesc", "region"),
                synthetic=False,
            ))
        return result

    @classmethod
    def parse_nowcast(cls, payload: Any) -> list[MeteorologyNowcastFrame]:
        items = cls._items(payload, "frames")
        result: list[MeteorologyNowcastFrame] = []
        for index, raw in enumerate(items):
            if not isinstance(raw, dict):
                continue
            offset = cls._first_int(raw, "offsetMinutes", "offset", "leadMinutes")
            valid_at = cls._first_datetime(raw, "validAt", "time", "forecastTime")
            if offset not in {0, 30, 60, 120} or valid_at is None:
                continue
            bbox = cls._bbox(raw.get("bbox") or raw.get("bounds"))
            crs = cls._first_text(raw, "crs", "coordinateReference")
            raster_url = cls._first_text(raw, "rasterUrl", "url", "imageUrl")
            preview_url = cls._first_text(raw, "previewUrl", "preview")
            media_type = cls._first_text(raw, "mediaType", "contentType")
            georeferenced = bool(crs and bbox)
            result.append(MeteorologyNowcastFrame(
                offsetMinutes=offset,
                validAt=valid_at,
                rasterUrl=raster_url,
                previewUrl=preview_url,
                mediaType=media_type,
                crs=crs,
                bbox=bbox,
                georeferenced=georeferenced,
                renderableInCesium=bool(georeferenced and raster_url),
                sourceId=cls._first_text(raw, "sourceId", "id") or f"NOWCAST-{index + 1}",
                synthetic=False,
            ))
        return sorted(result, key=lambda item: item.offsetMinutes)

    @staticmethod
    def _items(payload: Any, preferred_key: str) -> list[Any]:
        if isinstance(payload, list):
            return payload
        if not isinstance(payload, dict):
            return []
        for key in (preferred_key, "data", "items", "records"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
            if isinstance(value, dict):
                nested = value.get(preferred_key) or value.get("items") or value.get("records")
                if isinstance(nested, list):
                    return nested
        return []

    @staticmethod
    def _first_text(raw: dict[str, Any], *keys: str) -> str | None:
        for key in keys:
            value = raw.get(key)
            if value is None:
                continue
            text = str(value).strip()
            if text:
                return text
        return None

    @classmethod
    def _first_datetime(cls, raw: dict[str, Any], *keys: str) -> datetime | None:
        for key in keys:
            parsed = cls._datetime(raw.get(key))
            if parsed is not None:
                return parsed
        return None

    @staticmethod
    def _first_int(raw: dict[str, Any], *keys: str) -> int | None:
        for key in keys:
            try:
                return int(raw[key])
            except (KeyError, TypeError, ValueError):
                continue
        return None

    @staticmethod
    def _bbox(value: Any) -> list[float] | None:
        if not isinstance(value, (list, tuple)) or len(value) != 4:
            return None
        try:
            bbox = [float(item) for item in value]
        except (TypeError, ValueError):
            return None
        return bbox

    @staticmethod
    def _datetime(value: Any) -> datetime | None:
        if value is None:
            return None
        text = str(value).strip()
        if not text:
            return None
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            return None
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)

    @staticmethod
    def _url_or_none(value: str | None) -> str | None:
        if not value:
            return None
        parsed = urlparse(value)
        return value if parsed.scheme in {"http", "https"} and parsed.netloc else None

    @staticmethod
    def _health(provider: str, source_id: str, status: MeteorologySourceHealthStatus, received_at: datetime, message: str) -> MeteorologySourceHealth:
        return MeteorologySourceHealth(provider=provider, sourceId=source_id, status=status, receivedAt=received_at, message=message)
