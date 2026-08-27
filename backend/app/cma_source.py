from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin
from urllib.request import ProxyHandler, Request, build_opener
from zoneinfo import ZoneInfo

from .models import (
    MeteorologyCurrentConditions,
    MeteorologyNowcastFrame,
    MeteorologyRadarFrame,
    MeteorologySourceHealth,
    MeteorologySourceHealthStatus,
    MeteorologyWarning,
)

SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")


@dataclass(frozen=True)
class CmaContextResult:
    current: MeteorologyCurrentConditions | None
    warnings: list[MeteorologyWarning]
    radar_frames: list[MeteorologyRadarFrame]
    frames: list[MeteorologyNowcastFrame]
    source_health: list[MeteorologySourceHealth]
    observed_at: datetime | None


class CmaSourceAdapter:
    """Real public meteorology providers plus compatible override seams.

    Built-in MVP providers:
    - NMC current weather + radar preview: /rest/weather?stationid=...
    - NMC warning list: /rest/findAlarm?province=...
    - China Weather minute precipitation web product: 0-2h point nowcast

    `CMA_WARNING_URL` can override the warning JSON source.
    `CMA_NOWCAST_URL` can override the point nowcast with a verified metadata
    JSON endpoint. A custom nowcast frame is only marked Cesium-renderable when
    it contains rasterUrl + CRS + bbox. The built-in radar preview is real but
    intentionally NOT georeferenced because NMC's weather payload does not
    publish a trustworthy CRS/bbox contract.
    """

    CURRENT_SOURCE = "NMC_CURRENT_WEATHER"
    WARNING_SOURCE = "NMC_WEATHER_WARNING"
    RADAR_SOURCE = "NMC_RADAR_PREVIEW"
    NOWCAST_SOURCE = "CHINA_WEATHER_MINUTE_NOWCAST"
    CUSTOM_NOWCAST_SOURCE = "CMA_RADAR_NOWCAST"

    DEFAULT_STATION_ID = "58367"  # Shanghai national station used by NMC city weather page.
    DEFAULT_PROVINCE = "上海市"
    DEFAULT_LAT = 31.2304
    DEFAULT_LON = 121.4737
    NMC_WEATHER_URL_TEMPLATE = "https://www.nmc.cn/rest/weather?stationid={station_id}"
    NMC_WARNING_URL = "https://www.nmc.cn/rest/findAlarm"
    MINUTE_NOWCAST_URL_TEMPLATE = (
        "https://d3.weather.com.cn/webgis_rain_new/webgis/minute"
        "?lat={lat:.6f}&lon={lon:.6f}&callback=qixiao"
    )
    MINUTE_REFERER = "https://m.weather.com.cn/screen/rain_index_online.html"

    def __init__(
        self,
        *,
        station_id: str | None = None,
        province: str | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
        weather_url: str | None = None,
        warning_url: str | None = None,
        nowcast_url: str | None = None,
        minute_url_template: str | None = None,
        timeout_seconds: float = 8.0,
    ) -> None:
        self.station_id = (station_id or self.DEFAULT_STATION_ID).strip()
        self.province = (province or self.DEFAULT_PROVINCE).strip()
        self.latitude = self.DEFAULT_LAT if latitude is None else latitude
        self.longitude = self.DEFAULT_LON if longitude is None else longitude
        self.weather_url = self._url_or_none(weather_url) or self.NMC_WEATHER_URL_TEMPLATE.format(
            station_id=self.station_id
        )
        self.warning_url = self._url_or_none(warning_url)
        self.nowcast_url = self._url_or_none(nowcast_url)
        self.minute_url_template = (minute_url_template or self.MINUTE_NOWCAST_URL_TEMPLATE).strip()
        self.timeout_seconds = timeout_seconds if timeout_seconds > 0 else 8.0
        self._opener = build_opener(ProxyHandler({}))

    @classmethod
    def from_env(cls) -> "CmaSourceAdapter":
        return cls(
            station_id=os.getenv("NMC_STATION_ID", cls.DEFAULT_STATION_ID),
            province=os.getenv("NMC_ALARM_PROVINCE", cls.DEFAULT_PROVINCE),
            latitude=cls._env_float("METEOROLOGY_LAT", cls.DEFAULT_LAT),
            longitude=cls._env_float("METEOROLOGY_LON", cls.DEFAULT_LON),
            weather_url=os.getenv("NMC_WEATHER_URL", "").strip() or None,
            warning_url=os.getenv("CMA_WARNING_URL", "").strip() or None,
            nowcast_url=os.getenv("CMA_NOWCAST_URL", "").strip() or None,
            minute_url_template=os.getenv("CHINA_WEATHER_MINUTE_URL_TEMPLATE", "").strip() or None,
            timeout_seconds=cls._env_float("CMA_TIMEOUT_SECONDS", 8.0),
        )

    def fetch(self, received_at: datetime | None = None) -> CmaContextResult:
        received_at = received_at or datetime.now(timezone.utc)

        weather_payload: Any | None = None
        weather_error: Exception | None = None
        try:
            weather_payload = self._fetch_json(self.weather_url)
        except Exception as exc:  # Keep the other sources usable.
            weather_error = exc

        current, current_health = self._current_domain(weather_payload, weather_error, received_at)
        radar_frames, radar_health = self._radar_domain(weather_payload, weather_error, received_at)
        warnings, warning_health = self._warning_domain(received_at)
        frames, nowcast_health = self._nowcast_domain(received_at)

        observed: list[datetime] = []
        if current is not None:
            observed.append(current.observedAt)
        observed.extend(item.issuedAt for item in warnings)
        observed.extend(item.observedAt for item in radar_frames)
        observed.extend(item.validAt for item in frames)

        return CmaContextResult(
            current=current,
            warnings=warnings,
            radar_frames=radar_frames,
            frames=frames,
            source_health=[current_health, warning_health, radar_health, nowcast_health],
            observed_at=max(observed) if observed else None,
        )

    # ------------------------------------------------------------------
    # Current weather + radar preview from the same NMC weather payload.

    def _current_domain(
        self,
        payload: Any | None,
        error: Exception | None,
        received_at: datetime,
    ) -> tuple[MeteorologyCurrentConditions | None, MeteorologySourceHealth]:
        if error is not None:
            return None, self._health(
                self.CURRENT_SOURCE,
                self.weather_url,
                MeteorologySourceHealthStatus.UNAVAILABLE,
                received_at,
                str(error),
            )
        current = self.parse_nmc_current(payload)
        if current is None:
            return None, self._health(
                self.CURRENT_SOURCE,
                self.weather_url,
                MeteorologySourceHealthStatus.SCHEMA_MISMATCH,
                received_at,
                "NMC weather payload has no usable data.real current observation",
            )
        return current, MeteorologySourceHealth(
            provider=self.CURRENT_SOURCE,
            sourceId=self.weather_url,
            status=MeteorologySourceHealthStatus.OK,
            observedAt=current.observedAt,
            receivedAt=received_at,
            message=None,
        )

    def _radar_domain(
        self,
        payload: Any | None,
        error: Exception | None,
        received_at: datetime,
    ) -> tuple[list[MeteorologyRadarFrame], MeteorologySourceHealth]:
        if error is not None:
            return [], self._health(
                self.RADAR_SOURCE,
                self.weather_url,
                MeteorologySourceHealthStatus.UNAVAILABLE,
                received_at,
                str(error),
            )
        frames = self.parse_nmc_radar(payload, fallback_time=received_at)
        if not frames:
            return [], self._health(
                self.RADAR_SOURCE,
                self.weather_url,
                MeteorologySourceHealthStatus.SCHEMA_MISMATCH,
                received_at,
                "NMC weather payload has no radar preview image",
            )
        observed = max(item.observedAt for item in frames)
        return frames, MeteorologySourceHealth(
            provider=self.RADAR_SOURCE,
            sourceId=self.weather_url,
            status=MeteorologySourceHealthStatus.OK,
            observedAt=observed,
            receivedAt=received_at,
            message="REAL_PREVIEW_ONLY_NO_CRS_BBOX",
        )

    # ------------------------------------------------------------------
    # Warning provider.

    def _warning_domain(
        self, received_at: datetime
    ) -> tuple[list[MeteorologyWarning], MeteorologySourceHealth]:
        source_url = self.warning_url or self._nmc_warning_query_url()
        try:
            payload = self._fetch_json(source_url)
            warnings = (
                self.parse_generic_warnings(payload)
                if self.warning_url
                else self.parse_nmc_warnings(payload, province=self.province)
            )
            observed = max((item.issuedAt for item in warnings), default=None)
            return warnings, MeteorologySourceHealth(
                provider=self.WARNING_SOURCE,
                sourceId=source_url,
                status=MeteorologySourceHealthStatus.OK,
                observedAt=observed,
                receivedAt=received_at,
                message="No active warning returned" if not warnings else None,
            )
        except Exception as exc:
            return [], self._health(
                self.WARNING_SOURCE,
                source_url,
                MeteorologySourceHealthStatus.UNAVAILABLE,
                received_at,
                str(exc),
            )

    # ------------------------------------------------------------------
    # 0-2h precipitation nowcast. Custom metadata URL keeps the old seam.

    def _nowcast_domain(
        self, received_at: datetime
    ) -> tuple[list[MeteorologyNowcastFrame], MeteorologySourceHealth]:
        if self.nowcast_url:
            try:
                payload = self._fetch_json(self.nowcast_url)
                frames = self.parse_generic_nowcast(payload)
                if not frames:
                    raise RuntimeError("configured nowcast endpoint returned no usable frames")
                observed = max(item.validAt for item in frames)
                return frames, MeteorologySourceHealth(
                    provider=self.CUSTOM_NOWCAST_SOURCE,
                    sourceId=self.nowcast_url,
                    status=MeteorologySourceHealthStatus.OK,
                    observedAt=observed,
                    receivedAt=received_at,
                    message=None,
                )
            except Exception as exc:
                return [], self._health(
                    self.CUSTOM_NOWCAST_SOURCE,
                    self.nowcast_url,
                    MeteorologySourceHealthStatus.UNAVAILABLE,
                    received_at,
                    str(exc),
                )

        source_url = self._minute_nowcast_url()
        try:
            text = self._fetch_text(source_url, referer=self.MINUTE_REFERER)
            payload = self.decode_json_or_jsonp(text)
            frames = self.parse_minute_nowcast(payload, received_at=received_at)
            if not frames:
                raise RuntimeError("minute nowcast response has no usable 0-2h product")
            return frames, MeteorologySourceHealth(
                provider=self.NOWCAST_SOURCE,
                sourceId=source_url,
                status=MeteorologySourceHealthStatus.OK,
                observedAt=min(item.validAt for item in frames),
                receivedAt=received_at,
                message="POINT_NOWCAST_NOT_GEOREFERENCED_RASTER",
            )
        except Exception as exc:
            return [], self._health(
                self.NOWCAST_SOURCE,
                source_url,
                MeteorologySourceHealthStatus.UNAVAILABLE,
                received_at,
                str(exc),
            )

    # ------------------------------------------------------------------
    # Public parsers are intentionally testable without network.

    @classmethod
    def parse_nmc_current(cls, payload: Any) -> MeteorologyCurrentConditions | None:
        data = payload.get("data") if isinstance(payload, dict) else None
        real = data.get("real") if isinstance(data, dict) else None
        if not isinstance(real, dict):
            return None

        station = real.get("station") if isinstance(real.get("station"), dict) else {}
        weather = real.get("weather") if isinstance(real.get("weather"), dict) else {}
        wind = real.get("wind") if isinstance(real.get("wind"), dict) else {}
        observed_at = cls._first_datetime(
            real,
            "publish_time",
            "publishTime",
            "time",
            default_tz=SHANGHAI_TZ,
        )
        if observed_at is None:
            return None

        station_id = cls._first_text(station, "code", "stationid", "id") or cls.DEFAULT_STATION_ID
        station_name = cls._first_text(station, "city", "name") or "上海"
        return MeteorologyCurrentConditions(
            stationId=station_id,
            stationName=station_name,
            observedAt=observed_at,
            temperatureC=cls._finite_number(weather.get("temperature")),
            condition=cls._first_text(weather, "info", "weather", "text"),
            humidityPercent=cls._bounded_number(weather.get("humidity"), 0, 100),
            rainfallMm=cls._nonnegative_number(weather.get("rain")),
            windDirection=cls._first_text(wind, "direct", "direction"),
            windPower=cls._first_text(wind, "power", "scale"),
            sourceId=f"NMC:{station_id}",
            synthetic=False,
        )

    @classmethod
    def parse_nmc_radar(
        cls, payload: Any, *, fallback_time: datetime
    ) -> list[MeteorologyRadarFrame]:
        data = payload.get("data") if isinstance(payload, dict) else None
        radar = data.get("radar") if isinstance(data, dict) else None
        if not isinstance(radar, dict):
            return []
        image = cls._first_text(radar, "image", "img", "url")
        if not image:
            return []
        preview_url = urljoin("https://image.nmc.cn/", image)
        observed_at = cls._first_datetime(
            radar,
            "time",
            "observedAt",
            "publish_time",
            default_tz=SHANGHAI_TZ,
        ) or fallback_time
        return [MeteorologyRadarFrame(
            observedAt=observed_at,
            previewUrl=preview_url,
            mediaType="image/png" if preview_url.lower().endswith(".png") else "image/jpeg",
            crs=None,
            bbox=None,
            georeferenced=False,
            renderableInCesium=False,
            sourceId=cls._first_text(radar, "title") or "NMC_RADAR_PREVIEW",
            synthetic=False,
        )]

    @classmethod
    def parse_nmc_warnings(cls, payload: Any, *, province: str = "") -> list[MeteorologyWarning]:
        data = payload.get("data") if isinstance(payload, dict) else None
        page = data.get("page") if isinstance(data, dict) else None
        items = page.get("list") if isinstance(page, dict) else None
        if not isinstance(items, list):
            raise ValueError("NMC warning payload has no data.page.list")

        result: list[MeteorologyWarning] = []
        province_key = province.removesuffix("市").removesuffix("省")
        for index, raw in enumerate(items):
            if not isinstance(raw, dict):
                continue
            title = cls._first_text(raw, "title") or ""
            if province_key and province_key not in title:
                continue
            issued = cls._first_datetime(raw, "issuetime", "issuedAt", default_tz=SHANGHAI_TZ)
            if issued is None:
                continue
            warning_type, level = cls._warning_type_level(title)
            area = cls._warning_area(title)
            result.append(MeteorologyWarning(
                type=warning_type,
                level=level,
                issuedAt=issued,
                expiresAt=None,
                sourceId=cls._first_text(raw, "alertid", "id") or f"NMC-WARNING-{index + 1}",
                area=area,
                synthetic=False,
            ))
        return result

    @classmethod
    def parse_generic_warnings(cls, payload: Any) -> list[MeteorologyWarning]:
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
            result.append(MeteorologyWarning(
                type=warning_type,
                level=level,
                issuedAt=issued,
                expiresAt=cls._first_datetime(raw, "expiresAt", "expires", "expireTime"),
                sourceId=cls._first_text(raw, "sourceId", "identifier", "id") or f"WARNING-{index + 1}",
                area=cls._first_text(raw, "area", "areaDesc", "region"),
                synthetic=False,
            ))
        return result

    @classmethod
    def parse_generic_nowcast(cls, payload: Any) -> list[MeteorologyNowcastFrame]:
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
            precipitation = cls._nonnegative_number(
                raw.get("precipitationValue", raw.get("rainfallValue"))
            )
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
                summary=cls._first_text(raw, "summary", "message", "msg"),
                precipitationValue=precipitation,
                precipitationUnit=cls._first_text(raw, "precipitationUnit", "unit"),
                sourceId=cls._first_text(raw, "sourceId", "id") or f"NOWCAST-{index + 1}",
                synthetic=False,
            ))
        return sorted(result, key=lambda item: item.offsetMinutes)

    @classmethod
    def parse_minute_nowcast(
        cls, payload: Any, *, received_at: datetime
    ) -> list[MeteorologyNowcastFrame]:
        if not isinstance(payload, dict):
            return []
        summary = cls._first_text(payload, "msg", "message", "summary", "desc")
        times = cls._normalize_times(payload.get("times"))
        values = cls._find_numeric_series(payload)
        if not summary and not times and not values:
            return []

        frames: list[MeteorologyNowcastFrame] = []
        for offset in (0, 30, 60, 120):
            value: float | None = None
            if values:
                index = min(offset, len(values) - 1)
                value = cls._nonnegative_number(values[index])
            frames.append(MeteorologyNowcastFrame(
                offsetMinutes=offset,
                validAt=received_at + timedelta(minutes=offset),
                rasterUrl=None,
                previewUrl=None,
                mediaType=None,
                crs=None,
                bbox=None,
                georeferenced=False,
                renderableInCesium=False,
                summary=summary or "中国天气网未来两小时分钟级降水预报",
                precipitationValue=value,
                precipitationUnit=None,
                sourceId=f"CHINA_WEATHER_MINUTE:{offset}",
                synthetic=False,
            ))
        return frames

    @staticmethod
    def decode_json_or_jsonp(text: str) -> Any:
        text = text.strip().lstrip("\ufeff")
        if not text:
            raise ValueError("empty response")
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}")
            if start < 0 or end <= start:
                raise ValueError("response is neither JSON nor JSONP")
            return json.loads(text[start:end + 1])

    # ------------------------------------------------------------------
    # HTTP + helpers.

    def _fetch_json(self, url: str) -> Any:
        return json.loads(self._fetch_text(url))

    def _fetch_text(self, url: str, *, referer: str | None = None) -> str:
        headers = {
            "Accept": "application/json,text/plain,*/*",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151 Safari/537.36"
            ),
        }
        if referer:
            headers["Referer"] = referer
        request = Request(url, headers=headers)
        try:
            with self._opener.open(request, timeout=self.timeout_seconds) as response:
                if response.status != 200:
                    raise RuntimeError(f"HTTP {response.status}")
                raw = response.read()
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            raise RuntimeError(f"fetch failed: {exc}") from exc
        for encoding in ("utf-8", "gb18030"):
            try:
                return raw.decode(encoding)
            except UnicodeDecodeError:
                continue
        raise RuntimeError("response text decoding failed")

    def _nmc_warning_query_url(self) -> str:
        query = urlencode({
            "pageNo": 1,
            "pageSize": 50,
            "signaltype": "",
            "signallevel": "",
            "province": self.province,
        })
        return f"{self.NMC_WARNING_URL}?{query}"

    def _minute_nowcast_url(self) -> str:
        template = self.minute_url_template
        try:
            url = template.format(lat=self.latitude, lon=self.longitude)
        except (KeyError, ValueError) as exc:
            raise RuntimeError("CHINA_WEATHER_MINUTE_URL_TEMPLATE must accept {lat} and {lon}") from exc
        parsed = self._url_or_none(url)
        if parsed is None:
            raise RuntimeError("minute nowcast URL template produced an invalid URL")
        return parsed

    @staticmethod
    def _warning_type_level(title: str) -> tuple[str, str]:
        match = re.search(r"发布(.+?)(红色|橙色|黄色|蓝色)预警(?:信号)?", title)
        if match:
            return match.group(1).strip(), match.group(2)
        match = re.search(r"发布(.+?)预警(?:信号)?", title)
        if match:
            return match.group(1).strip(), "未分级"
        return title or "气象预警", "未分级"

    @staticmethod
    def _warning_area(title: str) -> str | None:
        match = re.match(r"(.+?气象台)发布", title)
        if not match:
            return None
        return match.group(1).removesuffix("气象台")

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
    def _first_text(raw: Any, *keys: str) -> str | None:
        if not isinstance(raw, dict):
            return None
        for key in keys:
            value = raw.get(key)
            if value is None:
                continue
            text = str(value).strip()
            if text and text.lower() not in {"none", "null", "9999", "9999.0"}:
                return text
        return None

    @classmethod
    def _first_datetime(
        cls,
        raw: Any,
        *keys: str,
        default_tz: ZoneInfo | timezone = timezone.utc,
    ) -> datetime | None:
        if not isinstance(raw, dict):
            return None
        for key in keys:
            parsed = cls._datetime(raw.get(key), default_tz=default_tz)
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
        if not all(-180 <= bbox[index] <= 180 for index in (0, 2)):
            return None
        if not all(-90 <= bbox[index] <= 90 for index in (1, 3)):
            return None
        return bbox

    @staticmethod
    def _datetime(
        value: Any, *, default_tz: ZoneInfo | timezone = timezone.utc
    ) -> datetime | None:
        if value is None:
            return None
        text = str(value).strip()
        if not text:
            return None
        candidates = [text.replace("Z", "+00:00")]
        for fmt in ("%Y/%m/%d %H:%M", "%Y-%m-%d %H:%M", "%Y%m%d%H%M", "%Y%m%d%H%M%S"):
            try:
                parsed = datetime.strptime(text, fmt)
                return parsed.replace(tzinfo=default_tz).astimezone(timezone.utc)
            except ValueError:
                continue
        try:
            parsed = datetime.fromisoformat(candidates[0])
        except ValueError:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=default_tz)
        return parsed.astimezone(timezone.utc)

    @staticmethod
    def _finite_number(value: Any) -> float | None:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return None
        if not (-999 <= number <= 999):
            return None
        return number

    @classmethod
    def _nonnegative_number(cls, value: Any) -> float | None:
        number = cls._finite_number(value)
        return number if number is not None and number >= 0 else None

    @classmethod
    def _bounded_number(cls, value: Any, minimum: float, maximum: float) -> float | None:
        number = cls._finite_number(value)
        return number if number is not None and minimum <= number <= maximum else None

    @staticmethod
    def _normalize_times(value: Any) -> list[str]:
        if isinstance(value, list):
            return [str(item) for item in value]
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return []

    @classmethod
    def _find_numeric_series(cls, payload: Any) -> list[float]:
        preferred = ("rain", "rainfall", "precipitation", "precip", "values", "series", "data")
        seen: set[int] = set()

        def visit(value: Any) -> list[float] | None:
            if isinstance(value, (dict, list)):
                identity = id(value)
                if identity in seen:
                    return None
                seen.add(identity)
            if isinstance(value, list) and len(value) >= 2:
                numbers: list[float] = []
                for item in value:
                    number = cls._nonnegative_number(item)
                    if number is None:
                        numbers = []
                        break
                    numbers.append(number)
                if numbers:
                    return numbers
                for item in value:
                    found = visit(item)
                    if found:
                        return found
            if isinstance(value, dict):
                for key in preferred:
                    if key in value:
                        found = visit(value[key])
                        if found:
                            return found
                for key, item in value.items():
                    if key in preferred:
                        continue
                    found = visit(item)
                    if found:
                        return found
            return None

        return visit(payload) or []

    @staticmethod
    def _url_or_none(value: str | None) -> str | None:
        if not value:
            return None
        from urllib.parse import urlparse

        parsed = urlparse(value)
        return value if parsed.scheme in {"http", "https"} and parsed.netloc else None

    @staticmethod
    def _env_float(name: str, default: float) -> float:
        raw = os.getenv(name, str(default)).strip()
        try:
            return float(raw)
        except ValueError:
            return default

    @staticmethod
    def _health(
        provider: str,
        source_id: str,
        status: MeteorologySourceHealthStatus,
        received_at: datetime,
        message: str,
    ) -> MeteorologySourceHealth:
        return MeteorologySourceHealth(
            provider=provider,
            sourceId=source_id,
            status=status,
            receivedAt=received_at,
            message=message,
        )
