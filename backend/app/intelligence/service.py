from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ..models import AIAnalysis, RiskAssessment, SensorState
from .forecast import EmpiricalForecastService, ScenarioCatalogMatcher, forecast_rain_30_mm
from .history import RiseRateEstimate, SensorDepthHistory
from .risk import RiskAssessmentService


class EventIntelligenceService:
    """Thin orchestration layer over the existing repository and realtime collectors."""

    def __init__(
        self,
        repository: Any,
        *,
        shanghai_water_realtime: Any = None,
        meteorology_realtime: Any = None,
    ) -> None:
        self.repository = repository
        self.shanghai_water_realtime = shanghai_water_realtime
        self.meteorology_realtime = meteorology_realtime
        self.history = SensorDepthHistory()
        self.risk_service = RiskAssessmentService()
        self.empirical_forecast = EmpiricalForecastService()
        self.scenario_matcher = ScenarioCatalogMatcher()

    def observe_sensor(self, state: SensorState) -> None:
        self.history.add(state)

    def get_event(self, event_id: str) -> dict[str, Any] | None:
        derived = self._derive(event_id)
        return None if derived is None else derived["event"]

    def get_risk(self, event_id: str) -> RiskAssessment | None:
        derived = self._derive(event_id)
        return None if derived is None else derived["risk"]

    def get_forecast(self, event_id: str) -> dict[str, Any] | None:
        derived = self._derive(event_id)
        if derived is None:
            return None
        return self._forecast_from_derived(derived)

    def get_analysis(self, event_id: str) -> dict[str, Any] | None:
        derived = self._derive(event_id)
        if derived is None:
            return None
        if derived["sensor"] is None:
            fallback = self.repository.get_analysis(event_id)
            if fallback is None:
                return None
            return {
                **fallback,
                "method": "SYNTHETIC_FIXTURE",
                "confidence": 0.2,
                "generatedAt": datetime.now(timezone.utc),
            }

        forecast = self._forecast_from_derived(derived)
        risk: RiskAssessment = derived["risk"]
        causes = []
        total = sum(item.contribution for item in risk.causes) or 1.0
        for item in risk.causes:
            causes.append(
                {
                    "label": item.label,
                    "weight": round(item.contribution / total, 4),
                    "feature": item.feature,
                    "rawValue": item.rawValue,
                    "contribution": item.contribution,
                }
            )

        plus10 = next((frame for frame in forecast["frames"] if frame["timeKey"] == "PLUS_10"), None)
        plus30 = next((frame for frame in forecast["frames"] if frame["timeKey"] == "PLUS_30"), None)
        forecast_summary = (
            f"+10 min {plus10['maxDepthCm']:.1f} cm，"
            f"+30 min {plus30['maxDepthCm']:.1f} cm；"
            f"{forecast.get('method', 'FORECAST')}"
            if plus10 and plus30 else "短时预测暂不可用"
        )

        return AIAnalysis(
            eventId=event_id,
            riskSummary=self._risk_summary(risk),
            causes=causes,
            forecastSummary=forecast_summary,
            actions=self._actions(risk),
            method=risk.method,
            confidence=risk.confidence,
            generatedAt=risk.generatedAt,
        ).model_dump(mode="json")

    def get_update(self, event_id: str) -> dict[str, Any] | None:
        event = self.get_event(event_id)
        if event is None:
            return None
        risk = self.get_risk(event_id)
        forecast = self.get_forecast(event_id)
        analysis = self.get_analysis(event_id)
        if risk is None or forecast is None or analysis is None:
            return None
        return {
            "event": event,
            "risk": risk.model_dump(mode="json"),
            "forecast": _json_ready(forecast),
            "analysis": analysis,
        }

    def get_update_for_sensor(self, sensor_id: str) -> dict[str, Any] | None:
        event_id = self._event_id_for_sensor(sensor_id)
        return self.get_update(event_id) if event_id else None

    def all_updates(self) -> list[dict[str, Any]]:
        event_ids = {
            point.get("eventId")
            for point in self.repository.list_flood_points()
            if point.get("eventId")
        }
        return [
            update for event_id in sorted(event_ids)
            if (update := self.get_update(str(event_id))) is not None
        ]

    def _derive(self, event_id: str) -> dict[str, Any] | None:
        base = self.repository.get_event(event_id)
        if base is None:
            return None
        event = dict(base)
        sensor_id = self._sensor_id_for_event(event_id)
        sensor = self.repository.get_state(sensor_id) if sensor_id else None
        if sensor is not None:
            self.history.add(sensor)
            event["currentDepthCm"] = sensor.depthCm
            rise = self.history.estimate(sensor.sensorId)
            event["riseRateCmMin"] = rise.value_cm_min if rise.available else 0.0
        else:
            rise = RiseRateEstimate(
                float(event.get("riseRateCmMin", 0.0)),
                0,
                10,
                "SCENARIO_BASELINE",
                "STABLE",
                False,
            )

        meteorology_state = (
            self.meteorology_realtime.state()
            if self.meteorology_realtime is not None else None
        )
        water_state = (
            self.shanghai_water_realtime.state()
            if self.shanghai_water_realtime is not None else None
        )
        risk = self.risk_service.assess(
            event_id=event_id,
            current_depth_cm=float(event["currentDepthCm"]),
            rise_rate_cm_min=rise.value_cm_min if rise.available else None,
            pipe_load_percent=float(event["pipeLoadPercent"]) if event.get("pipeLoadPercent") is not None else None,
            sensor=sensor,
            meteorology_state=meteorology_state,
            water_state=water_state,
        )
        event.update(
            {
                "riskLevel": risk.riskLevel.value,
                "riskIndex": risk.riskIndex,
                "riskMethod": risk.method,
                "riskConfidence": risk.confidence,
                "riseRateSource": rise.source,
            }
        )
        return {
            "event": event,
            "risk": risk,
            "sensor": sensor,
            "sensorId": sensor_id,
            "rise": rise,
            "meteorologyState": meteorology_state,
            "waterState": water_state,
        }

    def _forecast_from_derived(self, derived: dict[str, Any]) -> dict[str, Any]:
        event = derived["event"]
        event_id = str(event["id"])
        fixture = self.repository.get_forecast(event_id)
        sensor = derived["sensor"]
        if sensor is None:
            if fixture is None:
                return {
                    "eventId": event_id,
                    "generatedAt": datetime.now(timezone.utc),
                    "frames": [],
                    "method": "SYNTHETIC_FIXTURE",
                    "confidence": 0.1,
                    "inputStatus": "NO_LIVE_SENSOR",
                    "uncertaintyNote": "No live sensor state.",
                }
            return {
                **fixture,
                "method": "SYNTHETIC_FIXTURE",
                "confidence": 0.2,
                "inputStatus": "NO_LIVE_SENSOR",
                "uncertaintyNote": "Static scenario fallback until telemetry arrives.",
            }

        risk: RiskAssessment = derived["risk"]
        rise: RiseRateEstimate = derived["rise"]
        rain30 = forecast_rain_30_mm(derived["meteorologyState"])
        features = {
            "currentDepthCm": float(event["currentDepthCm"]),
            "riseRateCmMin": rise.value_cm_min if rise.available else 0.0,
            "forecastRain30Mm": rain30,
            "pipeLoadPercent": float(event.get("pipeLoadPercent", 0.0)),
        }
        generated_at = datetime.now(timezone.utc)
        scenario = self.scenario_matcher.match(
            event_id=event_id,
            features=features,
            fixture_forecast=fixture,
            generated_at=generated_at,
        )
        if scenario is not None:
            return scenario
        return self.empirical_forecast.forecast(
            event=event,
            risk=risk,
            rise_rate_cm_min=rise.value_cm_min,
            rise_rate_available=rise.available,
            forecast_rain_30_mm=rain30,
            fixture_forecast=fixture,
            generated_at=generated_at,
        )

    def _sensor_id_for_event(self, event_id: str) -> str | None:
        for point in self.repository.list_flood_points():
            if point.get("eventId") == event_id and point.get("sensorId"):
                return str(point["sensorId"])
        return None

    def _event_id_for_sensor(self, sensor_id: str) -> str | None:
        for point in self.repository.list_flood_points():
            if point.get("sensorId") == sensor_id and point.get("eventId"):
                return str(point["eventId"])
        return None

    @staticmethod
    def _risk_summary(risk: RiskAssessment) -> str:
        label = {
            "NORMAL": "当前风险较低",
            "WARNING": "当前进入关注状态",
            "HIGH": "当前为高风险状态",
            "CRITICAL": "当前为严重风险状态",
        }[risk.riskLevel.value]
        causes = "、".join(item.label for item in risk.causes[:2]) or "有效证据不足"
        return f"{label}，风险指数 {risk.riskIndex:.0f}/100；主要驱动：{causes}。"

    @staticmethod
    def _actions(risk: RiskAssessment) -> list[dict[str, Any]]:
        if risk.riskLevel.value in {"HIGH", "CRITICAL"}:
            return [
                {"priority": 1, "title": "交通管控", "detail": "根据现场阈值限制车辆进入积水路段。"},
                {"priority": 2, "title": "排水处置", "detail": "优先检查排水口并准备移动排水能力。"},
                {"priority": 3, "title": "持续复核", "detail": "持续比较 Sensor、气象与视频证据变化。"},
            ]
        if risk.riskLevel.value == "WARNING":
            return [
                {"priority": 1, "title": "加强监测", "detail": "缩短观测间隔并关注上涨速度。"},
                {"priority": 2, "title": "预置资源", "detail": "准备排水和交通管控资源。"},
            ]
        return [
            {"priority": 1, "title": "保持监测", "detail": "维持常规监测，等待新的实测或降雨变化。"}
        ]


def _json_ready(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _json_ready(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    return value
