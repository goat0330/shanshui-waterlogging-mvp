from __future__ import annotations

import json
import math
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, Request, build_opener

from .models import (
    Coordinates,
    ShanghaiWaterLevelForecast,
    ShanghaiWaterLevelStation,
    ShanghaiWaterPondingSite,
    ShanghaiWaterRainfallStation,
    ShanghaiWaterSnapshot,
    ShanghaiWaterSourceHealth,
    ShanghaiWaterSourceStatus,
)


class ShanghaiWaterError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class ShanghaiWaterAdapter:
    """Public Shanghai Water Bureau adapter with source-local normalization.

    Upstream field drift is absorbed here. The internal Pydantic/domain models
    remain strict. A small number of malformed upstream rows no longer turns an
    otherwise usable source into a total failure.
    """

    SOURCE = "SHANGHAI_WATER_BUREAU_PUBLIC"
    BASE_URL = "https://swgxh.swj.sh.gov.cn/swj/swj/businessConvenientService"
    COORDINATE_REFERENCE = "SOURCE_REPORTED_XX2000_YY2000"
    REQUIRED_FIELDS = {
        "SSYLMore": ("STATIONID", "STATIONNAME", "RAINVALUE", "DATETIME", "XX2000", "YY2000"),
        "JSJCMore": ("STATIONID", "STATIONNAME", "JISHUISTATUS", "DATETIME", "XX2000", "YY2000"),
        "SSSW": ("STATIONID", "STATIONNAME", "OUTWATER", "DATETIME", "XX2000", "YY2000"),
        "YJSW": ("STATIONID", "STATIONNAME", "YBCW", "DATETIME", "XX2000", "YY2000"),
    }
    # Only the three current-observation feeds are required for strict real mode.
    # Forecast is useful context but must not collapse a usable real snapshot.
    STRICT_REQUIRED_DATASETS = {"SSYLMore", "JSJCMore", "SSSW"}
    FIELD_ALIASES = {
        "STATIONID": ("STATION_ID", "STCD", "STATIONCODE", "ID"),
        "STATIONNAME": ("STATION_NAME", "STNM", "NAME"),
        "RAINVALUE": ("RAIN_VALUE", "RAINFALL", "RAIN", "VALUE"),
        "JISHUISTATUS": ("JISHUI", "DEPTH", "DEPTHCM", "WATERDEPTH"),
        "OUTWATER": ("OUT_WATER", "WATERLEVEL", "WATER_LEVEL", "WATERLEVELVALUE", "SW", "Z"),
        "YBCW": ("FORECASTWATER", "FORECAST_WATER_LEVEL", "FORECASTLEVEL"),
        "DATETIME": ("DATE_TIME", "OBSERVEDAT", "OBSERVED_AT", "UPDATETIME", "UPDATE_TIME", "TIME", "TM"),
        "XX2000": ("LON", "LONGITUDE", "LGTD", "X", "XX"),
        "YY2000": ("LAT", "LATITUDE", "LTTD", "Y", "YY"),
    }
    NUMERIC_FIELDS = {"RAINVALUE", "JISHUISTATUS", "OUTWATER", "YBCW", "XX2000", "YY2000"}
    SIGNED_NUMERIC_FIELDS = {"OUTWATER", "YBCW"}
    TEXT_FIELDS = {"STATIONID", "STATIONNAME"}

    def __init__(self, timeout_seconds: float = 8.0, cache_ttl_seconds: float = 45.0) -> None:
        if timeout_seconds <= 0 or cache_ttl_seconds <= 0:
            raise ValueError("Shanghai Water timeout and cache TTL must be positive")
        self.timeout_seconds = timeout_seconds
        self.cache_ttl_seconds = cache_ttl_seconds
        self._opener = build_opener(ProxyHandler({}))
        self._cache: tuple[datetime, ShanghaiWaterSnapshot] | None = None

    @property
    def source_urls(self) -> list[str]:
        return [f"{self.BASE_URL}/getList?type={name}" for name in ("SSYLMore", "JSJCMore", "SSSW", "YJSW")]

    def fetch(self, *, allow_partial: bool = True) -> ShanghaiWaterSnapshot:
        now = datetime.now(timezone.utc)
        if self._cache is not None:
            cached_at, cached_snapshot = self._cache
            if (now - cached_at).total_seconds() < self.cache_ttl_seconds:
                return cached_snapshot.model_copy(update={"cacheHit": True})

        parsers = {
            "SSYLMore": self._rainfall_item,
            "JSJCMore": self._ponding_item,
            "SSSW": self._level_item,
            "YJSW": self._forecast_item,
        }
        results: dict[str, list[Any]] = {}
        health: dict[str, ShanghaiWaterSourceHealth] = {}

        for dataset_type, parser in parsers.items():
            source_url = f"{self.BASE_URL}/getList?type={dataset_type}"
            try:
                raw_items = self._fetch_list(dataset_type)
                received_at = datetime.now(timezone.utc)
                parsed_items: list[Any] = []
                invalid_count = 0
                for raw in raw_items:
                    if not isinstance(raw, dict):
                        invalid_count += 1
                        continue
                    normalized = self._normalize_record(dataset_type, raw)
                    if not self._schema_valid(dataset_type, normalized):
                        invalid_count += 1
                        continue
                    item = parser(normalized, received_at, source_url)
                    if item is None:
                        invalid_count += 1
                    else:
                        parsed_items.append(item)

                results[dataset_type] = parsed_items
                if parsed_items:
                    # Row-level source noise is recorded but does not poison the
                    # entire dataset once canonical rows are available.
                    status = ShanghaiWaterSourceStatus.OK
                    error_code = None
                    fallback_reason = (
                        f"{invalid_count} upstream record(s) skipped after normalization"
                        if invalid_count
                        else None
                    )
                elif invalid_count:
                    status = ShanghaiWaterSourceStatus.SCHEMA_MISMATCH
                    error_code = "SHANGHAI_WATER_SCHEMA_MISMATCH"
                    fallback_reason = f"{invalid_count} upstream record(s) were unusable"
                else:
                    status = ShanghaiWaterSourceStatus.EMPTY
                    error_code = None
                    fallback_reason = None

                health[dataset_type] = ShanghaiWaterSourceHealth(
                    status=status,
                    sourceUrl=source_url,
                    recordCount=len(parsed_items),
                    observedLatestAt=self._latest_at(parsed_items),
                    fetchedAt=received_at,
                    errorCode=error_code,
                    fallbackReason=fallback_reason,
                )
            except ShanghaiWaterError as exc:
                status = (
                    ShanghaiWaterSourceStatus.SCHEMA_MISMATCH
                    if exc.code == "SHANGHAI_WATER_SCHEMA_MISMATCH"
                    else ShanghaiWaterSourceStatus.UNAVAILABLE
                )
                results[dataset_type] = []
                health[dataset_type] = ShanghaiWaterSourceHealth(
                    status=status,
                    sourceUrl=source_url,
                    recordCount=0,
                    fetchedAt=datetime.now(timezone.utc),
                    errorCode=exc.code,
                )

        strict_failures = [
            name
            for name in self.STRICT_REQUIRED_DATASETS
            if health[name].status != ShanghaiWaterSourceStatus.OK
        ]
        if not allow_partial and strict_failures:
            first_failure = health[strict_failures[0]]
            raise ShanghaiWaterError(
                first_failure.errorCode or "SHANGHAI_WATER_UNAVAILABLE",
                f"Required Shanghai Water source unavailable: {', '.join(sorted(strict_failures))}",
            )

        rainfall = sorted(results["SSYLMore"], key=lambda item: item.rainfallValue, reverse=True)
        ponding = sorted(results["JSJCMore"], key=lambda item: item.depthCm, reverse=True)
        levels = results["SSSW"]
        forecasts = results["YJSW"]
        if not rainfall and not ponding and not levels and not forecasts:
            raise ShanghaiWaterError("SHANGHAI_WATER_EMPTY", "Shanghai Water Bureau returned no usable observations")

        failed_sources = [name for name, item in health.items() if item.status != ShanghaiWaterSourceStatus.OK]
        completed_at = datetime.now(timezone.utc)
        snapshot = ShanghaiWaterSnapshot(
            source=self.SOURCE,
            fetchedAt=completed_at,
            receivedAt=completed_at,
            sourceStatus="ok" if not failed_sources else "partial",
            sourceHealth=health,
            coordinateReference=self.COORDINATE_REFERENCE,
            sourceUrls=self.source_urls,
            rainfall=rainfall,
            ponding=ponding,
            waterLevels=levels,
            waterLevelForecast=forecasts,
        )
        if not strict_failures:
            self._cache = (completed_at, snapshot)
        return snapshot

    def _fetch_list(self, dataset_type: str) -> list[Any]:
        url = f"{self.BASE_URL}/getList?type={dataset_type}"
        request = Request(url, headers={"Accept": "application/json", "User-Agent": "ShanshuiWaterloggingMVP/0.1"})
        try:
            with self._opener.open(request, timeout=self.timeout_seconds) as response:
                raw_body = response.read()
                status = response.status
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            raise ShanghaiWaterError("SHANGHAI_WATER_FETCH_FAILED", f"{dataset_type} fetch failed: {exc}") from exc
        if status != 200:
            raise ShanghaiWaterError("SHANGHAI_WATER_FETCH_FAILED", f"{dataset_type} returned HTTP {status}")
        try:
            payload = json.loads(raw_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ShanghaiWaterError("SHANGHAI_WATER_SCHEMA_MISMATCH", f"{dataset_type} returned invalid JSON") from exc
        if not isinstance(payload, dict) or str(payload.get("code")) != "200" or not isinstance(payload.get("data"), list):
            raise ShanghaiWaterError("SHANGHAI_WATER_SCHEMA_MISMATCH", f"{dataset_type} response has no data list")
        return payload["data"]

    @classmethod
    def _normalize_record(cls, dataset_type: str, raw: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(raw)
        lookup = {str(key).upper(): value for key, value in raw.items()}
        for canonical in cls.REQUIRED_FIELDS[dataset_type]:
            current = normalized.get(canonical)
            if current is not None and str(current).strip().lower() not in {"", "null", "none"}:
                continue
            for alias in cls.FIELD_ALIASES.get(canonical, ()):
                if alias.upper() in lookup:
                    normalized[canonical] = lookup[alias.upper()]
                    break
        # Optional metadata is normalized only when present; no synthetic values.
        for optional, aliases in {
            "QUYU": ("DISTRICT", "AREA"),
            "JZ": ("TOWNSHIP",),
            "HELIU": ("RIVER", "RIVERNAME"),
            "DATASOURCE": ("DATA_SOURCE", "SOURCE"),
        }.items():
            if cls._text(normalized.get(optional)):
                continue
            for alias in aliases:
                if alias.upper() in lookup:
                    normalized[optional] = lookup[alias.upper()]
                    break
        return normalized

    @classmethod
    def _schema_valid(cls, dataset_type: str, raw: dict[str, Any]) -> bool:
        for field in cls.REQUIRED_FIELDS[dataset_type]:
            if field not in raw:
                return False
            value = raw[field]
            if field in cls.NUMERIC_FIELDS and cls._number(value, allow_negative=field in cls.SIGNED_NUMERIC_FIELDS) is None:
                return False
            if field in cls.TEXT_FIELDS and not cls._text(value):
                return False
            if field == "DATETIME" and cls._datetime(value) is None:
                return False
        return True

    @staticmethod
    def _latest_at(items: list[Any]) -> datetime | None:
        timestamps = [getattr(item, "observedAt", None) or getattr(item, "forecastAt", None) for item in items]
        valid = [value for value in timestamps if isinstance(value, datetime)]
        return max(valid) if valid else None

    @classmethod
    def _rainfall_item(cls, raw: dict[str, Any], received_at: datetime, raw_source: str) -> ShanghaiWaterRainfallStation | None:
        value = cls._number(raw.get("RAINVALUE"))
        coordinates = cls._coordinates(raw)
        observed_at = cls._datetime(raw.get("DATETIME"))
        station_id = cls._text(raw.get("STATIONID"))
        station_name = cls._text(raw.get("STATIONNAME"))
        if value is None or coordinates is None or observed_at is None or not station_id or not station_name:
            return None
        return ShanghaiWaterRainfallStation(
            stationId=station_id, sourceId=station_id, stationName=station_name,
            district=cls._text(raw.get("QUYU")), township=cls._text(raw.get("JZ")),
            coordinates=coordinates, rainfallValue=value, observedAt=observed_at,
            receivedAt=received_at, provider=cls.SOURCE, rawSource=raw_source,
            dataSource=cls._text(raw.get("DATASOURCE")), isRaining=cls._bool(raw.get("ISRAINING")),
        )

    @classmethod
    def _ponding_item(cls, raw: dict[str, Any], received_at: datetime, raw_source: str) -> ShanghaiWaterPondingSite | None:
        depth = cls._number(raw.get("JISHUISTATUS"))
        coordinates = cls._coordinates(raw)
        observed_at = cls._datetime(raw.get("DATETIME"))
        site_id = cls._text(raw.get("STATIONID"))
        site_name = cls._text(raw.get("STATIONNAME"))
        if depth is None or coordinates is None or observed_at is None or not site_id or not site_name:
            return None
        return ShanghaiWaterPondingSite(
            siteId=site_id, sourceId=site_id, siteName=site_name,
            district=cls._text(raw.get("QUYU")), coordinates=coordinates, depthCm=depth,
            observedAt=observed_at, receivedAt=received_at, provider=cls.SOURCE,
            rawSource=raw_source, stage=cls._text(raw.get("FLLEVEL")),
            state=cls._text(raw.get("STATE")), dataSource=cls._text(raw.get("DATASOURCE")),
        )

    @classmethod
    def _level_item(cls, raw: dict[str, Any], received_at: datetime, raw_source: str) -> ShanghaiWaterLevelStation | None:
        level = cls._number(raw.get("OUTWATER"), allow_negative=True)
        coordinates = cls._coordinates(raw)
        observed_at = cls._datetime(raw.get("DATETIME"))
        station_id = cls._text(raw.get("STATIONID"))
        station_name = cls._text(raw.get("STATIONNAME"))
        if level is None or coordinates is None or observed_at is None or not station_id or not station_name:
            return None
        return ShanghaiWaterLevelStation(
            stationId=station_id, sourceId=station_id, stationName=station_name,
            district=cls._text(raw.get("QUYU")), river=cls._text(raw.get("HELIU")),
            coordinates=coordinates, outWaterM=level, observedAt=observed_at,
            receivedAt=received_at, provider=cls.SOURCE, rawSource=raw_source,
            dataSource=cls._text(raw.get("DATASOURCE")),
        )

    @classmethod
    def _forecast_item(cls, raw: dict[str, Any], received_at: datetime, raw_source: str) -> ShanghaiWaterLevelForecast | None:
        level = cls._number(raw.get("YBCW"), allow_negative=True)
        coordinates = cls._coordinates(raw)
        forecast_at = cls._datetime(raw.get("DATETIME"))
        station_id = cls._text(raw.get("STATIONID"))
        station_name = cls._text(raw.get("STATIONNAME"))
        if level is None or coordinates is None or forecast_at is None or not station_id or not station_name:
            return None
        return ShanghaiWaterLevelForecast(
            stationId=station_id, sourceId=station_id, stationName=station_name,
            coordinates=coordinates, forecastWaterLevelM=level, forecastAt=forecast_at,
            receivedAt=received_at, provider=cls.SOURCE, rawSource=raw_source,
        )

    @staticmethod
    def _text(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @staticmethod
    def _number(value: Any, *, allow_negative: bool = False) -> float | None:
        if value is None or str(value).strip().lower() in {"", "null", "none", "--", "-"}:
            return None
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        if not math.isfinite(number):
            return None
        if not allow_negative and number < 0:
            return None
        return number

    @staticmethod
    def _bool(value: Any) -> bool | None:
        text = str(value).strip().lower() if value is not None else ""
        if text in {"1", "true", "yes", "y"}:
            return True
        if text in {"0", "false", "no", "n"}:
            return False
        return None

    @staticmethod
    def _datetime(value: Any) -> datetime | None:
        text = str(value).strip() if value is not None else ""
        if not text or text.lower() in {"null", "none"}:
            return None
        candidates = (
            lambda: datetime.fromisoformat(text.replace("Z", "+00:00")),
            lambda: datetime.strptime(text, "%Y-%m-%d %H:%M:%S"),
            lambda: datetime.strptime(text, "%Y-%m-%d %H:%M"),
            lambda: datetime.strptime(text, "%Y/%m/%d %H:%M:%S"),
            lambda: datetime.strptime(text, "%Y/%m/%d %H:%M"),
        )
        parsed: datetime | None = None
        for parse in candidates:
            try:
                parsed = parse()
                break
            except ValueError:
                continue
        if parsed is None:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone(timedelta(hours=8)))
        return parsed

    @classmethod
    def _coordinates(cls, raw: dict[str, Any]) -> Coordinates | None:
        latitude = cls._number(raw.get("YY2000"))
        longitude = cls._number(raw.get("XX2000"))
        if latitude is None or longitude is None or latitude > 90 or longitude > 180:
            return None
        return Coordinates(lat=latitude, lon=longitude)
