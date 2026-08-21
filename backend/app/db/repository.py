from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import create_engine, func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import sessionmaker

from ..models import Coordinates, SensorRegistryEntry, SensorState, SensorType, TelemetryObservation
from ..repository import (
    FixtureRepository,
    UnknownSensorError,
    build_sensor_state,
)
from .schema import (
    cameras as cameras_table,
    flood_events as flood_events_table,
    flood_points as flood_points_table,
    forecast_frames as forecast_frames_table,
    sensor_flood_mappings as sensor_flood_mappings_table,
    sensor_latest_state as sensor_latest_state_table,
    sensor_observations as sensor_observations_table,
    sensors as sensors_table,
    sites as sites_table,
)


class PostgresRepository:
    """SQLAlchemy Core repository; schema creation belongs to Alembic."""

    backend = "postgres"

    def __init__(self, fixture_repository: FixtureRepository, database_url: str | None) -> None:
        if not database_url:
            raise ValueError("DATABASE_URL is required for the postgres repository")
        self.fixture_repository = fixture_repository
        self.engine = create_engine(database_url, pool_pre_ping=True)
        self.session_factory = sessionmaker(self.engine, expire_on_commit=False)

    @property
    def dashboard_overview(self) -> Any:
        return self.fixture_repository.dashboard_overview

    @property
    def rainfall(self) -> Any:
        return self.fixture_repository.rainfall

    def list_rainfall_station_ranking(self) -> list[dict[str, Any]]:
        return self.fixture_repository.get_rainfall_station_ranking()

    @property
    def forecast_adapter(self) -> Any:
        return self.fixture_repository.forecast_adapter

    @property
    def analysis_adapter(self) -> Any:
        return self.fixture_repository.analysis_adapter

    def list_flood_points(self) -> list[dict[str, Any]]:
        statement = select(
            flood_points_table.c.point_id.label("id"),
            flood_points_table.c.name,
            flood_points_table.c.district,
            func.ST_Y(flood_points_table.c.geom).label("lat"),
            func.ST_X(flood_points_table.c.geom).label("lon"),
            flood_points_table.c.depth_cm,
            flood_points_table.c.risk_level,
            flood_points_table.c.trend,
        ).order_by(flood_points_table.c.point_id)
        with self.session_factory() as session:
            rows = session.execute(statement).mappings().all()
        return [
            {
                "id": row["id"],
                "name": row["name"],
                "district": row["district"],
                "coordinates": {"lat": float(row["lat"]), "lon": float(row["lon"])},
                "depthCm": row["depth_cm"],
                "riskLevel": row["risk_level"],
                "trend": row["trend"],
            }
            for row in rows
        ]

    def get_event(self, event_id: str) -> dict[str, Any] | None:
        statement = select(
            flood_events_table.c.event_id.label("id"),
            flood_events_table.c.name,
            flood_events_table.c.district,
            flood_events_table.c.event_type,
            func.ST_Y(flood_events_table.c.geom).label("lat"),
            func.ST_X(flood_events_table.c.geom).label("lon"),
            flood_events_table.c.current_depth_cm,
            flood_events_table.c.rise_rate_cm_min,
            flood_events_table.c.pipe_load_percent,
            flood_events_table.c.risk_level,
            flood_events_table.c.started_at,
            flood_events_table.c.duration_seconds,
            flood_events_table.c.camera_id,
        ).where(flood_events_table.c.event_id == event_id)
        with self.session_factory() as session:
            row = session.execute(statement).mappings().one_or_none()
        if row is None:
            return None
        return {
            "id": row["id"],
            "name": row["name"],
            "district": row["district"],
            "eventType": row["event_type"],
            "coordinates": {"lat": float(row["lat"]), "lon": float(row["lon"])},
            "currentDepthCm": row["current_depth_cm"],
            "riseRateCmMin": row["rise_rate_cm_min"],
            "pipeLoadPercent": row["pipe_load_percent"],
            "riskLevel": row["risk_level"],
            "startedAt": row["started_at"],
            "durationSeconds": row["duration_seconds"],
            "cameraId": row["camera_id"],
        }

    def get_forecast(self, event_id: str) -> dict[str, Any] | None:
        statement = select(
            forecast_frames_table.c.event_id,
            forecast_frames_table.c.generated_at,
            forecast_frames_table.c.time_key,
            forecast_frames_table.c.offset_minutes,
            forecast_frames_table.c.max_depth_cm,
            forecast_frames_table.c.affected_area_km2,
            forecast_frames_table.c.geometry_url,
        ).where(forecast_frames_table.c.event_id == event_id).order_by(
            forecast_frames_table.c.offset_minutes
        )
        with self.session_factory() as session:
            rows = session.execute(statement).mappings().all()
        if not rows:
            return None
        return {
            "eventId": event_id,
            "generatedAt": rows[0]["generated_at"],
            "frames": [
                {
                    "timeKey": row["time_key"],
                    "offsetMinutes": row["offset_minutes"],
                    "maxDepthCm": row["max_depth_cm"],
                    "affectedAreaKm2": row["affected_area_km2"],
                    "geometryUrl": row["geometry_url"],
                }
                for row in rows
            ],
        }

    def get_analysis(self, event_id: str) -> dict[str, Any] | None:
        return self.fixture_repository.get_analysis(event_id)

    def list_cameras(self) -> list[dict[str, Any]]:
        statement = select(
            cameras_table.c.camera_id.label("id"),
            cameras_table.c.name,
            func.ST_Y(cameras_table.c.geom).label("lat"),
            func.ST_X(cameras_table.c.geom).label("lon"),
            cameras_table.c.status,
            cameras_table.c.media_type,
            cameras_table.c.media_url,
            cameras_table.c.overlay_url,
        ).order_by(cameras_table.c.camera_id)
        with self.session_factory() as session:
            rows = session.execute(statement).mappings().all()
        return [self._camera_from_row(row) for row in rows]

    def get_camera(self, camera_id: str) -> dict[str, Any] | None:
        statement = select(
            cameras_table.c.camera_id.label("id"),
            cameras_table.c.name,
            func.ST_Y(cameras_table.c.geom).label("lat"),
            func.ST_X(cameras_table.c.geom).label("lon"),
            cameras_table.c.status,
            cameras_table.c.media_type,
            cameras_table.c.media_url,
            cameras_table.c.overlay_url,
        ).where(cameras_table.c.camera_id == camera_id)
        with self.session_factory() as session:
            row = session.execute(statement).mappings().one_or_none()
        return None if row is None else self._camera_from_row(row)

    def get_timeline(self, scenario_id: str) -> dict[str, Any] | None:
        return self.fixture_repository.get_timeline(scenario_id)

    def get_entry(self, sensor_id: str) -> SensorRegistryEntry | None:
        statement = select(
            sensors_table.c.sensor_id,
            sensors_table.c.site_id,
            sensors_table.c.name,
            sensors_table.c.sensor_type,
            sensors_table.c.enabled,
            func.ST_Y(sites_table.c.geom).label("lat"),
            func.ST_X(sites_table.c.geom).label("lon"),
        ).join(sites_table, sensors_table.c.site_id == sites_table.c.site_id).where(
            sensors_table.c.sensor_id == sensor_id
        )
        with self.session_factory() as session:
            row = session.execute(statement).mappings().one_or_none()
        return None if row is None else self._entry_from_row(row)

    def get_state(self, sensor_id: str) -> SensorState | None:
        statement = select(
            sensor_latest_state_table.c.sensor_id,
            sensor_latest_state_table.c.site_id,
            sensor_latest_state_table.c.observed_at,
            sensor_latest_state_table.c.received_at,
            sensor_latest_state_table.c.depth_mm,
            sensor_latest_state_table.c.depth_cm,
            sensor_latest_state_table.c.water_detected,
            sensor_latest_state_table.c.sequence,
            sensor_latest_state_table.c.transport,
            sensor_latest_state_table.c.battery_mv,
            sensor_latest_state_table.c.signal_dbm,
            sensor_latest_state_table.c.source,
            func.ST_Y(sites_table.c.geom).label("lat"),
            func.ST_X(sites_table.c.geom).label("lon"),
        ).join(sites_table, sensor_latest_state_table.c.site_id == sites_table.c.site_id).where(
            sensor_latest_state_table.c.sensor_id == sensor_id
        )
        with self.session_factory() as session:
            row = session.execute(statement).mappings().one_or_none()
        return None if row is None else self._state_from_row(row)

    def record_observation(
        self,
        payload: TelemetryObservation,
        received_at: datetime,
        source: str,
    ) -> SensorState:
        with self.session_factory() as session:
            with session.begin():
                sensor_statement = select(
                    sensors_table.c.sensor_id,
                    sensors_table.c.site_id,
                    sensors_table.c.name,
                    sensors_table.c.sensor_type,
                    sensors_table.c.enabled,
                    func.ST_Y(sites_table.c.geom).label("lat"),
                    func.ST_X(sites_table.c.geom).label("lon"),
                ).join(sites_table, sensors_table.c.site_id == sites_table.c.site_id).where(
                    sensors_table.c.sensor_id == payload.sensorId
                )
                sensor_row = session.execute(sensor_statement).mappings().one_or_none()
                if sensor_row is None or not sensor_row["enabled"]:
                    raise UnknownSensorError(payload.sensorId)

                sensor = self._entry_from_row(sensor_row)
                state = build_sensor_state(payload, sensor, received_at, source)
                session.execute(
                    sensor_observations_table.insert().values(
                        sensor_id=state.sensorId,
                        observed_at=state.observedAt,
                        received_at=state.receivedAt,
                        depth_mm=state.depthMm,
                        depth_cm=state.depthCm,
                        water_detected=state.waterDetected,
                        sequence=state.sequence,
                        transport=state.transport.value if state.transport else None,
                        battery_mv=state.batteryMv,
                        signal_dbm=state.signalDbm,
                        source=state.source,
                    )
                )

                latest_values = {
                    "sensor_id": state.sensorId,
                    "site_id": state.siteId,
                    "observed_at": state.observedAt,
                    "received_at": state.receivedAt,
                    "depth_mm": state.depthMm,
                    "depth_cm": state.depthCm,
                    "water_detected": state.waterDetected,
                    "sequence": state.sequence,
                    "transport": state.transport.value if state.transport else None,
                    "battery_mv": state.batteryMv,
                    "signal_dbm": state.signalDbm,
                    "source": state.source,
                }
                upsert = pg_insert(sensor_latest_state_table).values(latest_values)
                upsert = upsert.on_conflict_do_update(
                    index_elements=[sensor_latest_state_table.c.sensor_id],
                    set_={
                        key: getattr(upsert.excluded, key)
                        for key in latest_values
                        if key != "sensor_id"
                    },
                )
                session.execute(upsert)

                mapping_statement = select(
                    sensor_flood_mappings_table.c.flood_point_id,
                    sensor_flood_mappings_table.c.event_id,
                ).where(sensor_flood_mappings_table.c.sensor_id == state.sensorId)
                mapping = session.execute(mapping_statement).mappings().one_or_none()
                if mapping is not None:
                    session.execute(
                        update(flood_points_table)
                        .where(flood_points_table.c.point_id == mapping["flood_point_id"])
                        .values(depth_cm=state.depthCm)
                    )
                    session.execute(
                        update(flood_events_table)
                        .where(flood_events_table.c.event_id == mapping["event_id"])
                        .values(current_depth_cm=state.depthCm)
                    )
        return state

    @staticmethod
    def _entry_from_row(row: Any) -> SensorRegistryEntry:
        return SensorRegistryEntry(
            sensorId=row["sensor_id"],
            siteId=row["site_id"],
            name=row["name"],
            coordinates=Coordinates(lat=float(row["lat"]), lon=float(row["lon"])),
            sensorType=SensorType(row["sensor_type"]),
            enabled=row["enabled"],
        )

    @staticmethod
    def _state_from_row(row: Any) -> SensorState:
        return SensorState(
            sensorId=row["sensor_id"],
            siteId=row["site_id"],
            coordinates=Coordinates(lat=float(row["lat"]), lon=float(row["lon"])),
            depthMm=row["depth_mm"],
            depthCm=row["depth_cm"],
            waterDetected=row["water_detected"],
            observedAt=row["observed_at"],
            receivedAt=row["received_at"],
            sequence=row["sequence"],
            transport=row["transport"],
            batteryMv=row["battery_mv"],
            signalDbm=row["signal_dbm"],
            source=row["source"],
        )

    @staticmethod
    def _camera_from_row(row: Any) -> dict[str, Any]:
        return {
            "id": row["id"],
            "name": row["name"],
            "coordinates": {"lat": float(row["lat"]), "lon": float(row["lon"])},
            "status": row["status"],
            "mediaType": row["media_type"],
            "mediaUrl": row["media_url"],
            "overlayUrl": row["overlay_url"],
        }
