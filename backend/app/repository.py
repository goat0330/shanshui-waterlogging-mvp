from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .adapters import AnalysisAdapter, ForecastAdapter
from .config import Settings, load_settings
from .models import (
    Coordinates,
    SensorRegistryEntry,
    SensorState,
    SensorType,
    TelemetryObservation,
)


class UnknownSensorError(LookupError):
    pass


def build_sensor_state(
    payload: TelemetryObservation,
    sensor: SensorRegistryEntry,
    received_at: datetime,
    source: str,
) -> SensorState:
    return SensorState(
        sensorId=payload.sensorId,
        siteId=sensor.siteId,
        coordinates=sensor.coordinates,
        observedAt=payload.observedAt,
        receivedAt=received_at,
        depthMm=payload.depthMm,
        depthCm=payload.depthMm / 10,
        waterDetected=payload.depthMm > 0,
        sequence=payload.sequence,
        transport=payload.transport,
        batteryMv=payload.batteryMv,
        signalDbm=payload.signalDbm,
        source=source,
    )


class FixtureRepository:
    """Read-only repository over the checked-in Contract fixtures."""

    def __init__(self, fixture_dir: Path | None = None) -> None:
        self.fixture_dir = fixture_dir or Path(__file__).resolve().parents[2] / "contracts" / "fixtures"
        self.dashboard_overview = self._load("dashboard-overview.json")
        self.rainfall = self._load("rainfall-current.json")
        self.rainfall_station_ranking = self._load("rainfall-stations-ranking.json")
        self.flood_points = self._load("flood-points.json")
        self.cameras = self._index("cameras.json", "id")
        self.events = self._index_glob("event-*.json", "id")
        self.forecast_adapter = ForecastAdapter(self.fixture_dir, self.events.keys())
        self.analysis_adapter = AnalysisAdapter(self.fixture_dir, self.events.keys())
        self.timelines = self._index_glob("timeline-*.json", "scenarioId")
        mapping = self._load("sensor-floodpoint-mapping.json")
        self.sensor_mappings = {mapping["sensorId"]: mapping}
        self.flood_point_mappings = {mapping["floodPointId"]: mapping}

    def _load(self, filename: str) -> Any:
        with (self.fixture_dir / filename).open("r", encoding="utf-8") as file:
            return json.load(file)

    def _index(self, filename: str, key: str) -> dict[str, dict[str, Any]]:
        return {str(item[key]): item for item in self._load(filename)}

    def _index_glob(self, pattern: str, key: str) -> dict[str, dict[str, Any]]:
        result: dict[str, dict[str, Any]] = {}
        for path in sorted(self.fixture_dir.glob(pattern)):
            with path.open("r", encoding="utf-8") as file:
                item = json.load(file)
            result[str(item[key])] = item
        return result

    def get_dashboard_overview(self) -> dict[str, Any]:
        """Project the optional situation block from the checked-in fixtures."""

        events = list(self.events.values())
        depths = [float(point["depthCm"]) for point in self.flood_points]
        updated_at = datetime.fromisoformat(str(self.dashboard_overview["updatedAt"]))
        disposition = {"pending": 0, "handling": 0, "relieved": 0}
        districts: dict[str, int] = {}
        response_minutes: list[float] = []
        new_today = 0
        change_vs_hour = 0.0

        for event in events:
            depth_cm = float(event.get("currentDepthCm", 0))
            risk_level = str(event.get("riskLevel", "NORMAL"))
            if depth_cm <= 0 or risk_level == "NORMAL":
                disposition["relieved"] += 1
            elif risk_level in {"HIGH", "CRITICAL"}:
                disposition["handling"] += 1
            else:
                disposition["pending"] += 1

            district = str(event.get("district", "未分区"))
            districts[district] = districts.get(district, 0) + 1
            rise_rate = event.get("riseRateCmMin")
            if rise_rate is not None:
                change_vs_hour += float(rise_rate) * 60
            duration_seconds = event.get("durationSeconds")
            if duration_seconds is not None:
                response_minutes.append(float(duration_seconds) / 60)
            started_at = event.get("startedAt")
            if started_at and datetime.fromisoformat(str(started_at)).date() == updated_at.date():
                new_today += 1

        sorted_districts = sorted(districts.items(), key=lambda item: (-item[1], item[0]))
        avg_depth = sum(depths) / len(depths) if depths else 0.0
        avg_response = sum(response_minutes) / len(response_minutes) if response_minutes else 0.0
        situation = {
            "totalEvents": len(events),
            "changeVsHour": round(change_vs_hour, 1),
            "disposition": disposition,
            "topDistricts": [
                {"district": district, "eventCount": event_count}
                for district, event_count in sorted_districts
            ],
            "metrics": {
                "maxDepthCm": max(depths, default=0.0),
                "avgDepthCm": round(avg_depth, 1),
                "avgResponseMinutes": round(avg_response, 1),
                "newToday": new_today,
            },
            "source": "FIXTURE_DERIVED",
        }
        return {**self.dashboard_overview, "waterloggingSituation": situation}

    def get_event(self, event_id: str) -> dict[str, Any] | None:
        return self.events.get(event_id)

    def get_forecast(self, event_id: str) -> dict[str, Any] | None:
        return self.forecast_adapter.get(event_id)

    def get_analysis(self, event_id: str) -> dict[str, Any] | None:
        return self.analysis_adapter.get(event_id)

    def get_rainfall_station_ranking(self) -> list[dict[str, Any]]:
        return sorted(
            self.rainfall_station_ranking,
            key=lambda item: item["intensityMmH"],
            reverse=True,
        )

    def get_camera(self, camera_id: str) -> dict[str, Any] | None:
        return self.cameras.get(camera_id)

    def get_timeline(self, scenario_id: str) -> dict[str, Any] | None:
        return self.timelines.get(scenario_id)

    def project_sensor_depth(self, sensor_id: str, depth_cm: float) -> None:
        mapping = self.sensor_mappings.get(sensor_id)
        if mapping is None:
            return

        for flood_point in self.flood_points:
            if flood_point["id"] == mapping["floodPointId"]:
                flood_point["depthCm"] = depth_cm
                break

        event = self.events.get(mapping["eventId"])
        if event is not None:
            event["currentDepthCm"] = depth_cm


class SensorRepository:
    """In-memory registry and latest state; state is lost on process restart."""

    def __init__(self) -> None:
        self._devices = {
            "SSZJ-NODE-001": SensorRegistryEntry(
                sensorId="SSZJ-NODE-001",
                siteId="SITE-RML-BJDD",
                name="人民路 × 滨江大道积水感知节点",
                coordinates=Coordinates(lat=31.2297, lon=121.4874),
                sensorType=SensorType.WATER_DEPTH,
                enabled=True,
            )
        }
        self._latest: dict[str, SensorState] = {}

    def get_entry(self, sensor_id: str) -> SensorRegistryEntry | None:
        return self._devices.get(sensor_id)

    def get_state(self, sensor_id: str) -> SensorState | None:
        return self._latest.get(sensor_id)

    def save_latest(self, state: SensorState) -> None:
        self._latest[state.sensorId] = state


class MemoryRepository:
    """Application repository backed by fixtures and process memory."""

    backend = "memory"

    def __init__(self, fixture_repository: FixtureRepository | None = None) -> None:
        self.fixture_repository = fixture_repository or FixtureRepository()
        self.sensor_repository = SensorRepository()

    @property
    def dashboard_overview(self) -> Any:
        return self.fixture_repository.get_dashboard_overview()

    @property
    def rainfall(self) -> Any:
        return self.fixture_repository.rainfall

    def list_rainfall_station_ranking(self) -> list[dict[str, Any]]:
        return self.fixture_repository.get_rainfall_station_ranking()

    @property
    def forecast_adapter(self) -> ForecastAdapter:
        return self.fixture_repository.forecast_adapter

    @property
    def analysis_adapter(self) -> AnalysisAdapter:
        return self.fixture_repository.analysis_adapter

    def list_flood_points(self) -> list[dict[str, Any]]:
        return [
            {
                **point,
                "eventId": self.fixture_repository.flood_point_mappings.get(point["id"], {}).get("eventId"),
                "sensorId": self.fixture_repository.flood_point_mappings.get(point["id"], {}).get("sensorId"),
            }
            for point in self.fixture_repository.flood_points
        ]

    def get_event(self, event_id: str) -> dict[str, Any] | None:
        return self.fixture_repository.get_event(event_id)

    def get_forecast(self, event_id: str) -> dict[str, Any] | None:
        return self.fixture_repository.get_forecast(event_id)

    def get_analysis(self, event_id: str) -> dict[str, Any] | None:
        return self.fixture_repository.get_analysis(event_id)

    def list_cameras(self) -> list[dict[str, Any]]:
        return list(self.fixture_repository.cameras.values())

    def get_camera(self, camera_id: str) -> dict[str, Any] | None:
        return self.fixture_repository.get_camera(camera_id)

    def get_timeline(self, scenario_id: str) -> dict[str, Any] | None:
        return self.fixture_repository.get_timeline(scenario_id)

    def get_entry(self, sensor_id: str) -> SensorRegistryEntry | None:
        return self.sensor_repository.get_entry(sensor_id)

    def get_state(self, sensor_id: str) -> SensorState | None:
        return self.sensor_repository.get_state(sensor_id)

    def record_observation(
        self,
        payload: TelemetryObservation,
        received_at: datetime,
        source: str,
    ) -> SensorState:
        sensor = self.sensor_repository.get_entry(payload.sensorId)
        if sensor is None or not sensor.enabled:
            raise UnknownSensorError(payload.sensorId)

        state = build_sensor_state(payload, sensor, received_at, source)
        self.sensor_repository.save_latest(state)
        self.fixture_repository.project_sensor_depth(state.sensorId, state.depthCm)
        return state


def build_repository(settings: Settings | None = None) -> MemoryRepository | Any:
    settings = settings or load_settings()
    fixture_repository = FixtureRepository()
    if settings.repository_backend == "memory":
        return MemoryRepository(fixture_repository)
    if settings.repository_backend == "postgres":
        from .db.repository import PostgresRepository

        return PostgresRepository(fixture_repository, settings.database_url)
    raise ValueError(f"Unsupported repository backend: {settings.repository_backend}")
