from __future__ import annotations

import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..models import RiskAssessment


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


class ScenarioCatalogMatcher:
    """Dependency-free kNN matcher over an optional precomputed SWMM catalog."""

    METHOD = "SCENARIO_LIBRARY"

    def __init__(self, catalog_path: Path | None = None) -> None:
        configured = os.getenv("FORECAST_SCENARIO_CATALOG", "").strip()
        self.path = catalog_path or (
            Path(configured) if configured
            else Path(__file__).resolve().parents[3] / "data" / "runtime" / "forecast-scenarios.json"
        )
        self._cache: tuple[float, dict[str, Any]] | None = None

    def match(
        self,
        *,
        event_id: str,
        features: dict[str, float | None],
        fixture_forecast: dict[str, Any] | None,
        generated_at: datetime,
    ) -> dict[str, Any] | None:
        catalog = self._load()
        if not catalog:
            return None
        records = [
            item for item in catalog.get("scenarios", [])
            if isinstance(item, dict) and item.get("eventId") in {None, event_id}
        ]
        ranges = catalog.get("featureRanges", {})
        usable_keys = [
            key for key, value in features.items()
            if value is not None and key in ranges
        ]
        if len(usable_keys) < 2 or not records:
            return None

        ranked: list[tuple[float, dict[str, Any]]] = []
        for record in records:
            record_features = record.get("features", {})
            if not all(key in record_features for key in usable_keys):
                continue
            squared = 0.0
            for key in usable_keys:
                bounds = ranges[key]
                minimum, maximum = float(bounds[0]), float(bounds[1])
                scale = max(maximum - minimum, 1e-6)
                squared += ((float(features[key]) - float(record_features[key])) / scale) ** 2
            ranked.append((math.sqrt(squared / len(usable_keys)), record))
        if not ranked:
            return None

        ranked.sort(key=lambda item: item[0])
        top = ranked[:3]
        if top[0][0] > 0.6:
            return None

        weights = [1.0 / (distance + 0.05) for distance, _ in top]
        weight_sum = sum(weights)
        fixture_by_key = {
            frame["timeKey"]: frame
            for frame in (fixture_forecast or {}).get("frames", [])
            if isinstance(frame, dict)
        }

        frames = []
        for key, offset in (("NOW", 0), ("PLUS_10", 10), ("PLUS_30", 30)):
            values = []
            lowers = []
            uppers = []
            areas = []
            best_geometry = None
            for rank_index, ((_, record), weight) in enumerate(zip(top, weights)):
                frame = next(
                    (item for item in record.get("frames", []) if item.get("timeKey") == key),
                    None,
                )
                if not frame:
                    continue
                values.append((float(frame["maxDepthCm"]), weight))
                if frame.get("lowerDepthCm") is not None:
                    lowers.append((float(frame["lowerDepthCm"]), weight))
                if frame.get("upperDepthCm") is not None:
                    uppers.append((float(frame["upperDepthCm"]), weight))
                if frame.get("affectedAreaKm2") is not None:
                    areas.append((float(frame["affectedAreaKm2"]), weight))
                if rank_index == 0 and frame.get("geometryUrl"):
                    best_geometry = str(frame["geometryUrl"])
            if not values:
                return None
            depth = sum(value * weight for value, weight in values) / sum(weight for _, weight in values)
            base = fixture_by_key.get(key, {})
            lower = (
                sum(value * weight for value, weight in lowers) / sum(weight for _, weight in lowers)
                if lowers else max(0.0, depth - 5.0)
            )
            upper = (
                sum(value * weight for value, weight in uppers) / sum(weight for _, weight in uppers)
                if uppers else depth + 5.0
            )
            frames.append(
                {
                    "timeKey": key,
                    "offsetMinutes": offset,
                    "maxDepthCm": round(depth, 1),
                    "lowerDepthCm": round(lower, 1),
                    "upperDepthCm": round(upper, 1),
                    "affectedAreaKm2": round(
                        sum(value * weight for value, weight in areas) / sum(weight for _, weight in areas), 4
                    ) if areas else float(base.get("affectedAreaKm2", 0.0)),
                    "geometryUrl": best_geometry or str(base.get("geometryUrl", "")),
                }
            )

        confidence = _clamp(0.92 - top[0][0] * 0.7, 0.35, 0.9)
        return {
            "eventId": event_id,
            "generatedAt": generated_at,
            "frames": frames,
            "method": self.METHOD,
            "confidence": round(confidence, 2),
            "inputStatus": "PRECOMPUTED_PHYSICS_MATCH",
            "uncertaintyNote": f"Top-3 normalized scenario match; best distance={top[0][0]:.3f}",
        }

    def _load(self) -> dict[str, Any] | None:
        if not self.path.exists():
            return None
        mtime = self.path.stat().st_mtime
        if self._cache and self._cache[0] == mtime:
            return self._cache[1]
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if not isinstance(payload, dict) or not isinstance(payload.get("scenarios"), list):
            return None
        self._cache = (mtime, payload)
        return payload


class EmpiricalForecastService:
    METHOD = "EMPIRICAL_BASELINE"

    def __init__(self, config_path: Path | None = None) -> None:
        path = config_path or Path(__file__).resolve().parents[2] / "config" / "empirical_forecast.json"
        with path.open("r", encoding="utf-8") as handle:
            self.config = json.load(handle)

    def forecast(
        self,
        *,
        event: dict[str, Any],
        risk: RiskAssessment,
        rise_rate_cm_min: float,
        rise_rate_available: bool,
        forecast_rain_30_mm: float | None,
        fixture_forecast: dict[str, Any] | None,
        generated_at: datetime | None = None,
    ) -> dict[str, Any]:
        generated_at = generated_at or datetime.now(timezone.utc)
        current = max(0.0, float(event["currentDepthCm"]))
        pipe_load = _clamp(float(event.get("pipeLoadPercent", 0.0)), 0.0, 100.0)
        rise = _clamp(float(rise_rate_cm_min), -2.0, 3.0) if rise_rate_available else 0.0
        rain30 = max(0.0, float(forecast_rain_30_mm or 0.0))

        fixture_by_key = {
            frame["timeKey"]: frame
            for frame in (fixture_forecast or {}).get("frames", [])
            if isinstance(frame, dict)
        }
        frames = []
        for key, horizon in (("NOW", 0), ("PLUS_10", 10), ("PLUS_30", 30)):
            if horizon == 0:
                predicted = current
            else:
                rise_effect = rise * horizon * float(self.config["risePersistence"])
                rain_effect = (
                    rain30
                    * float(self.config["rainToDepthCmPerMm"])
                    * (horizon / 30.0)
                )
                drainage_relief = (
                    (1.0 - pipe_load / 100.0)
                    * horizon
                    * float(self.config["drainageReliefCmPerMinAtZeroLoad"])
                )
                predicted = max(0.0, current + rise_effect + rain_effect - drainage_relief)

            uncertainty = (
                float(self.config["uncertaintyBaseCm"])
                + horizon * float(self.config["uncertaintyCmPerMinute"])
                + (1.0 - risk.confidence) * float(self.config["lowConfidencePenaltyCm"])
                + (0.0 if rise_rate_available else float(self.config["insufficientHistoryPenaltyCm"]))
            )
            lower = max(0.0, predicted - uncertainty)
            upper = predicted + uncertainty

            base = fixture_by_key.get(key, {})
            fixture_depth = max(float(base.get("maxDepthCm", predicted or 1.0)), 1.0)
            base_area = max(float(base.get("affectedAreaKm2", 0.0)), 0.0)
            area_ratio = _clamp(predicted / fixture_depth if fixture_depth else 1.0, 0.25, 2.0)
            frames.append(
                {
                    "timeKey": key,
                    "offsetMinutes": horizon,
                    "maxDepthCm": round(predicted, 1),
                    "lowerDepthCm": round(lower, 1),
                    "upperDepthCm": round(upper, 1),
                    "affectedAreaKm2": round(base_area * area_ratio, 4),
                    "geometryUrl": str(base.get("geometryUrl", "")),
                }
            )

        confidence = _clamp(
            risk.confidence * (0.85 if rise_rate_available else 0.55),
            0.15,
            0.85,
        )
        return {
            "eventId": str(event["id"]),
            "generatedAt": generated_at,
            "frames": frames,
            "method": self.METHOD,
            "confidence": round(confidence, 2),
            "inputStatus": "LIVE_DERIVED_DEPTH_SCENARIO_FOOTPRINT" if rise_rate_available else "LIVE_DEPTH_LIMITED_HISTORY_SCENARIO_FOOTPRINT",
            "uncertaintyNote": "Depth is dynamically derived by the empirical baseline; map footprint remains the existing scenario geometry until a reviewed scenario/PySWMM catalog supplies geometry.",
        }


def forecast_rain_30_mm(meteorology_state: Any) -> float | None:
    context = getattr(meteorology_state, "context", None)
    nowcast = getattr(context, "nowcast", None)
    frames = getattr(nowcast, "frames", []) if nowcast is not None else []
    candidates = []
    for frame in frames:
        if getattr(frame, "precipitationValue", None) is None:
            continue
        unit = str(getattr(frame, "precipitationUnit", "mm") or "mm").lower()
        if unit not in {"mm", "millimeter", "millimetre"}:
            continue
        offset = int(getattr(frame, "offsetMinutes", 999))
        if offset in {30, 60}:
            candidates.append((abs(offset - 30), float(frame.precipitationValue)))
    return max(0.0, min(candidates)[1]) if candidates else None
