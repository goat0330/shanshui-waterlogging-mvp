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
    """Small stdlib adapter for the public Shanghai Water Bureau JSON endpoints."""

    SOURCE = "SHANGHAI_WATER_BUREAU_PUBLIC"
    BASE_URL = "https://swgxh.swj.sh.gov.cn/swj/swj/businessConvenientService"
    COORDINATE_REFERENCE = "SOURCE_REPORTED_XX2000_YY2000"
    REQUIRED_FIELDS = {
        "SSYLMore": ("STATIONID", "STATIONNAME", "RAINVALUE", "DATETIME", "XX2000", "YY2000"),
        "JSJCMore": ("STATIONID", "STATIONNAME", "JISHUISTATUS", "DATETIME", "XX2000", "YY2000"),
        "SSSW": ("STATIONID", "STATIONNAME", "OUTWATER", "DATETIME", "XX2000", "YY2000"),
        "YJSW": ("STATIONID", "STATIONNAME", "YBCW", "DATETIME", "XX2000", "YY2000"),
    }
    NUMERIC_FIELDS = {"RAINVALUE", "JISHUISTATUS", "OUTWATER", "YBCW", "XX2000", "YY2000"}
    MEASUREMENT_FIELDS = {"RAINVALUE", "JISHUISTATUS", "OUTWATER", "YBCW"}
    MEASUREMENT_FIELD_BY_DATASET = {
        "SSYLMore": "RAINVALUE",
        "JSJCMore": "JISHUISTATUS",
        "SSSW": "OUTWATER",
        "YJSW": "YBCW",
    }
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
        return [
            f"{self.BASE_URL}/getList?type=SSYLMore",
            f"{self.BASE_URL}/getList?type=JSJCMore",
            f"{self.BASE_URL}/getList?type=SSSW",
            f"{self.BASE_URL}/getList?type=YJSW",
        ]

    def fetch(self, *, allow_partial: bool = True) -> ShanghaiWaterSnapshot:
        now = datetime.now(timezone.utc)
        if self._cache is not None:
            cached_at, cached_snapshot = self._cache
            cache_age = (now - cached_at).total_seconds()
            if cache_age < self.cache_ttl_seconds:
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
                    if not isinstance(raw, dict) or not self._schema_valid(dataset_type, raw):
                        invalid_count += 1
                        continue
                    item = parser(raw, received_at, source_url)
                    if item is None:
                        if not self._missing_measurement(raw.get(self.MEASUREMENT_FIELD_BY_DATASET[dataset_type])):
                            invalid_count += 1
                    else:
                        parsed_items.append(item)
                results[dataset_type] = parsed_items
                status = (
                    ShanghaiWaterSourceStatus.SCHEMA_MISMATCH
                    if invalid_count
                    else ShanghaiWaterSourceStatus.OK
                    if parsed_items
                    else ShanghaiWaterSourceStatus.EMPTY
                )
                health[dataset_type] = ShanghaiWaterSourceHealth(
                    status=status,
                    sourceUrl=source_url,
                    recordCount=len(parsed_items),
                    observedLatestAt=self._latest_at(parsed_items),
                    fetchedAt=received_at,
                    errorCode="SHANGHAI_WATER_SCHEMA_MISMATCH" if invalid_count else None,
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

        failed_sources = [name for name, item in health.items() if item.status != ShanghaiWaterSourceStatus.OK]
        if not allow_partial and failed_sources:
            first_failure = health[failed_sources[0]]
            raise ShanghaiWaterError(
                first_failure.errorCode or "SHANGHAI_WATER_UNAVAILABLE",
                f"Shanghai Water source unavailable: {', '.join(failed_sources)}",
            )

        rainfall = sorted(results["SSYLMore"], key=lambda item: item.rainfallValue, reverse=True)
        ponding = sorted(results["JSJCMore"], key=lambda item: item.depthCm, reverse=True)
        levels = results["SSSW"]
        forecasts = results["YJSW"]
        if not rainfall and not ponding and not levels and not forecasts:
            raise ShanghaiWaterError("SHANGHAI_WATER_EMPTY", "Shanghai Water Bureau returned no usable observations")

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
        if not failed_sources:
            self._cache = (completed_at, snapshot)
        return snapshot

    def _fetch_list(self, dataset_type: str) -> list[Any]:
        url = f"{self.BASE_URL}/getList?type={dataset_type}"
        request = Request(
            url,
            headers={
                "Accept": "application/json",
                "User-Agent": "ShanshuiWaterloggingMVP/0.1",
            },
        )
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
            raise ShanghaiWaterError(
                "SHANGHAI_WATER_SCHEMA_MISMATCH", f"{dataset_type} returned invalid JSON"
            ) from exc
        if not isinstance(payload, dict) or str(payload.get("code")) != "200" or not isinstance(payload.get("data"), list):
            raise ShanghaiWaterError(
                "SHANGHAI_WATER_SCHEMA_MISMATCH", f"{dataset_type} response has no data list"
            )
        return payload["data"]

    @classmethod
    def _schema_valid(cls, dataset_type: str, raw: dict[str, Any]) -> bool:
        for field in cls.REQUIRED_FIELDS[dataset_type]:
            if field not in raw:
                return False
            value = raw[field]
            if field in cls.NUMERIC_FIELDS and cls._number(value) is None:
                if field not in cls.MEASUREMENT_FIELDS or not cls._missing_measurement(value):
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
    def _rainfall_item(
        cls, raw: dict[str, Any], received_at: datetime, raw_source: str
    ) -> ShanghaiWaterRainfallStation | None:
        value = cls._number(raw.get("RAINVALUE"))
        coordinates = cls._coordinates(raw)
        observed_at = cls._datetime(raw.get("DATETIME"))
        station_id = cls._text(raw.get("STATIONID"))
        station_name = cls._text(raw.get("STATIONNAME"))
        if value is None or coordinates is None or observed_at is None or not station_id or not station_name:
            return None
        return ShanghaiWaterRainfallStation(
            stationId=station_id,
            sourceId=station_id,
            stationName=station_name,
            district=cls._text(raw.get("QUYU")),
            township=cls._text(raw.get("JZ")),
            coordinates=coordinates,
            rainfallValue=value,
            observedAt=observed_at,
            receivedAt=received_at,
            provider=cls.SOURCE,
            rawSource=raw_source,
            dataSource=cls._text(raw.get("DATASOURCE")),
            isRaining=cls._bool(raw.get("ISRAINING")),
        )

    @classmethod
    def _ponding_item(
        cls, raw: dict[str, Any], received_at: datetime, raw_source: str
    ) -> ShanghaiWaterPondingSite | None:
        depth = cls._number(raw.get("JISHUISTATUS"))
        coordinates = cls._coordinates(raw)
        observed_at = cls._datetime(raw.get("DATETIME"))
        site_id = cls._text(raw.get("STATIONID"))
        site_name = cls._text(raw.get("STATIONNAME"))
        if depth is None or coordinates is None or observed_at is None or not site_id or not site_name:
            return None
        return ShanghaiWaterPondingSite(
            siteId=site_id,
            sourceId=site_id,
            siteName=site_name,
            district=cls._text(raw.get("QUYU")),
            coordinates=coordinates,
            depthCm=depth,
            observedAt=observed_at,
            receivedAt=received_at,
            provider=cls.SOURCE,
            rawSource=raw_source,
            stage=cls._text(raw.get("FLLEVEL")),
            state=cls._text(raw.get("STATE")),
            dataSource=cls._text(raw.get("DATASOURCE")),
        )

    @classmethod
    def _level_item(
        cls, raw: dict[str, Any], received_at: datetime, raw_source: str
    ) -> ShanghaiWaterLevelStation | None:
        level = cls._number(raw.get("OUTWATER"))
        coordinates = cls._coordinates(raw)
        observed_at = cls._datetime(raw.get("DATETIME"))
        station_id = cls._text(raw.get("STATIONID"))
        station_name = cls._text(raw.get("STATIONNAME"))
        if level is None or coordinates is None or observed_at is None or not station_id or not station_name:
            return None
        return ShanghaiWaterLevelStation(
            stationId=station_id,
            sourceId=station_id,
            stationName=station_name,
            district=cls._text(raw.get("QUYU")),
            river=cls._text(raw.get("HELIU")),
            coordinates=coordinates,
            outWaterM=level,
            observedAt=observed_at,
            receivedAt=received_at,
            provider=cls.SOURCE,
            rawSource=raw_source,
            dataSource=cls._text(raw.get("DATASOURCE")),
        )

    @classmethod
    def _forecast_item(
        cls, raw: dict[str, Any], received_at: datetime, raw_source: str
    ) -> ShanghaiWaterLevelForecast | None:
        level = cls._number(raw.get("YBCW"))
        coordinates = cls._coordinates(raw)
        forecast_at = cls._datetime(raw.get("DATETIME"))
        station_id = cls._text(raw.get("STATIONID"))
        station_name = cls._text(raw.get("STATIONNAME"))
        if level is None or coordinates is None or forecast_at is None or not station_id or not station_name:
            return None
        return ShanghaiWaterLevelForecast(
            stationId=station_id,
            sourceId=station_id,
            stationName=station_name,
            coordinates=coordinates,
            forecastWaterLevelM=level,
            forecastAt=forecast_at,
            receivedAt=received_at,
            provider=cls.SOURCE,
            rawSource=raw_source,
        )

    @staticmethod
    def _text(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @staticmethod
    def _number(value: Any) -> float | None:
        if value is None or str(value).strip().lower() in {"", "null", "none"}:
            return None
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        return number if math.isfinite(number) and number >= 0 else None

    @staticmethod
    def _missing_measurement(value: Any) -> bool:
        return value is None or str(value).strip().lower() in {"", "null", "none"}

    @staticmethod
    def _bool(value: Any) -> bool | None:
        text = str(value).strip().lower() if value is not None else ""
        if text in {"1", "true", "yes"}:
            return True
        if text in {"0", "false", "no"}:
            return False
        return None

    @staticmethod
    def _datetime(value: Any) -> datetime | None:
        text = str(value).strip() if value is not None else ""
        if not text or text.lower() in {"null", "none"}:
            return None
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            try:
                parsed = datetime.strptime(text, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                try:
                    parsed = datetime.strptime(text, "%Y-%m-%d %H:%M")
                except ValueError:
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
