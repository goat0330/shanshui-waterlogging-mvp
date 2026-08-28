from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..models import RiskAssessment, RiskContribution, RiskLevel, SensorState


def _clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return max(minimum, min(maximum, value))


def _status_value(value: Any) -> str:
    return str(getattr(value, "value", value or "")).lower()


class RiskAssessmentService:
    """Explainable weighted risk + hard safety rules.

    This is a risk index, not a probability. External source uncertainty changes
    confidence; it does not silently turn missing evidence into "normal".
    """

    METHOD = "RULE_WEIGHTED_V1"

    def __init__(self, config_path: Path | None = None) -> None:
        path = config_path or Path(__file__).resolve().parents[2] / "config" / "risk_weights.json"
        with path.open("r", encoding="utf-8") as handle:
            self.config = json.load(handle)

    def assess(
        self,
        *,
        event_id: str,
        current_depth_cm: float,
        rise_rate_cm_min: float | None,
        pipe_load_percent: float | None,
        sensor: SensorState | None,
        meteorology_state: Any = None,
        water_state: Any = None,
        generated_at: datetime | None = None,
    ) -> RiskAssessment:
        generated_at = generated_at or datetime.now(timezone.utc)
        forecast_rain_30 = self._forecast_rain_30(meteorology_state)

        raw_features: dict[str, tuple[float | None, str, str]] = {
            "depthCm": (current_depth_cm, "当前水深", "cm"),
            "riseRateCmMin": (rise_rate_cm_min, "上涨速度", "cm/min"),
            "forecastRain30Mm": (forecast_rain_30, "未来30分钟降雨", "mm"),
            # Existing event.pipeLoadPercent is currently a scenario baseline,
            # not a live pipe-network telemetry source.
            "pipeLoadPercent": (pipe_load_percent, "场景管网负荷", "%"),
        }

        scales = self.config["scales"]
        base_weights = self.config["weights"]
        available_weight = sum(
            float(base_weights[key])
            for key, (value, _, _) in raw_features.items()
            if value is not None
        ) or 1.0

        contributions: list[RiskContribution] = []
        risk_index = 0.0
        for key, (value, label, unit) in raw_features.items():
            if value is None:
                continue
            if key == "riseRateCmMin":
                normalized = _clamp(max(0.0, float(value)) / float(scales[key]))
            else:
                normalized = _clamp(float(value) / float(scales[key]))
            weight = float(base_weights[key]) / available_weight
            contribution = normalized * weight * 100
            risk_index += contribution
            contributions.append(
                RiskContribution(
                    feature=key,
                    label=label,
                    rawValue=round(float(value), 3),
                    unit=unit,
                    normalized=round(normalized, 4),
                    weight=round(weight, 4),
                    contribution=round(contribution, 2),
                )
            )

        hard_rules: list[str] = []
        hard_floor = RiskLevel.NORMAL
        hard = self.config["hardRules"]
        if current_depth_cm >= float(hard["criticalDepthCm"]):
            hard_floor = RiskLevel.CRITICAL
            risk_index = max(risk_index, 85.0)
            hard_rules.append("DEPTH_CRITICAL")
        elif current_depth_cm >= float(hard["highDepthCm"]):
            hard_floor = RiskLevel.HIGH
            risk_index = max(risk_index, 70.0)
            hard_rules.append("DEPTH_HIGH")

        if rise_rate_cm_min is not None and rise_rate_cm_min >= float(hard["rapidRiseCmMin"]):
            if current_depth_cm >= float(hard["rapidRiseMinDepthCm"]):
                if hard_floor in {RiskLevel.NORMAL, RiskLevel.WARNING}:
                    hard_floor = RiskLevel.HIGH
                risk_index = max(risk_index, 65.0)
                hard_rules.append("RAPID_RISE")

        confidence = self._confidence(
            sensor=sensor,
            meteorology_state=meteorology_state,
            water_state=water_state,
            generated_at=generated_at,
            hard_rules=hard_rules,
        )
        risk_index = max(0.0, min(100.0, risk_index))
        level = self._level(risk_index)
        level = self._max_level(level, hard_floor)

        return RiskAssessment(
            eventId=event_id,
            generatedAt=generated_at,
            riskIndex=round(risk_index, 1),
            riskLevel=level,
            confidence=round(confidence, 2),
            method=self.METHOD,
            causes=sorted(contributions, key=lambda item: item.contribution, reverse=True),
            hardRulesTriggered=hard_rules,
            evidence={
                "sensor": "LIVE" if sensor is not None else "MISSING",
                "meteorology": _status_value(getattr(meteorology_state, "status", None)) or "missing",
                "shanghaiWater": _status_value(getattr(water_state, "status", None)) or "missing",
                "pipeLoad": "SCENARIO_BASELINE" if pipe_load_percent is not None else "MISSING",
            },
        )

    def _level(self, score: float) -> RiskLevel:
        thresholds = self.config["thresholds"]
        if score >= float(thresholds["critical"]):
            return RiskLevel.CRITICAL
        if score >= float(thresholds["high"]):
            return RiskLevel.HIGH
        if score >= float(thresholds["warning"]):
            return RiskLevel.WARNING
        return RiskLevel.NORMAL

    @staticmethod
    def _max_level(left: RiskLevel, right: RiskLevel) -> RiskLevel:
        order = {
            RiskLevel.NORMAL: 0,
            RiskLevel.WARNING: 1,
            RiskLevel.HIGH: 2,
            RiskLevel.CRITICAL: 3,
        }
        return left if order[left] >= order[right] else right

    def _forecast_rain_30(self, meteorology_state: Any) -> float | None:
        context = getattr(meteorology_state, "context", None)
        nowcast = getattr(context, "nowcast", None)
        frames = getattr(nowcast, "frames", []) if nowcast is not None else []
        candidates = [
            frame for frame in frames
            if getattr(frame, "offsetMinutes", None) in {30, 60}
            and getattr(frame, "precipitationValue", None) is not None
            and str(getattr(frame, "precipitationUnit", "mm") or "mm").lower() in {"mm", "millimeter", "millimetre"}
        ]
        if not candidates:
            return None
        candidates.sort(key=lambda frame: abs(int(frame.offsetMinutes) - 30))
        return max(0.0, float(candidates[0].precipitationValue))

    def _confidence(
        self,
        *,
        sensor: SensorState | None,
        meteorology_state: Any,
        water_state: Any,
        generated_at: datetime,
        hard_rules: list[str],
    ) -> float:
        confidence = 0.25
        if sensor is None:
            hard_rules.append("NO_LIVE_SENSOR")
        else:
            received = sensor.receivedAt
            if received.tzinfo is None:
                received = received.replace(tzinfo=timezone.utc)
            age_minutes = max(
                0.0,
                (generated_at - received.astimezone(timezone.utc)).total_seconds() / 60,
            )
            if age_minutes <= 2:
                confidence += 0.5
            elif age_minutes <= 10:
                confidence += 0.3
                hard_rules.append("SENSOR_DELAYED")
            else:
                hard_rules.append("SENSOR_STALE")
                confidence = min(confidence, 0.35)

        if _status_value(getattr(meteorology_state, "status", None)) == "ready":
            confidence += 0.15
        if _status_value(getattr(water_state, "status", None)) == "ready":
            confidence += 0.10
        return _clamp(confidence)
