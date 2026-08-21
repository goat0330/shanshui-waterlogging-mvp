from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from ..repository import FixtureRepository, SensorRepository
from .schema import (
    cameras,
    flood_events,
    flood_points,
    forecast_frames,
    sensor_flood_mappings,
    sensors,
    sites,
)


SITE_ID = "SITE-RML-BJDD"
SENSOR_ID = "SSZJ-NODE-001"
FLOOD_POINT_ID = "FP-001"
EVENT_ID = "FP202506010024"
CAMERA_ID = "CAM-017"


def seed_database(engine: Engine, fixture_dir: Path | None = None) -> dict[str, int]:
    fixtures = FixtureRepository(fixture_dir)
    sensor = SensorRepository().get_entry(SENSOR_ID)
    if sensor is None:
        raise ValueError(f"Missing demo sensor registry entry: {SENSOR_ID}")

    flood_point = next(item for item in fixtures.flood_points if item["id"] == FLOOD_POINT_ID)
    event = fixtures.events[EVENT_ID]
    camera = fixtures.cameras[CAMERA_ID]
    mapping = fixtures.sensor_mappings[SENSOR_ID]
    forecast = fixtures.forecast_adapter.get(EVENT_ID)
    if forecast is None:
        raise ValueError(f"Missing validated forecast fixture: {EVENT_ID}")

    with Session(engine) as session:
        with session.begin():
            _upsert(
                session,
                sites,
                {
                    "site_id": SITE_ID,
                    "name": sensor.name,
                    "geom": _point(sensor.coordinates.lon, sensor.coordinates.lat),
                },
                ["site_id"],
            )
            _upsert(
                session,
                flood_points,
                {
                    "point_id": flood_point["id"],
                    "name": flood_point["name"],
                    "district": flood_point.get("district"),
                    "geom": _point(
                        flood_point["coordinates"]["lon"], flood_point["coordinates"]["lat"]
                    ),
                    "depth_cm": flood_point["depthCm"],
                    "risk_level": flood_point["riskLevel"],
                    "trend": flood_point["trend"],
                },
                ["point_id"],
            )
            _upsert(
                session,
                cameras,
                {
                    "camera_id": camera["id"],
                    "name": camera["name"],
                    "geom": _point(camera["coordinates"]["lon"], camera["coordinates"]["lat"]),
                    "status": camera["status"],
                    "media_type": camera["mediaType"],
                    "media_url": camera["mediaUrl"],
                    "overlay_url": camera.get("overlayUrl"),
                },
                ["camera_id"],
            )
            _upsert(
                session,
                flood_events,
                {
                    "event_id": event["id"],
                    "name": event["name"],
                    "district": event["district"],
                    "event_type": event["eventType"],
                    "geom": _point(event["coordinates"]["lon"], event["coordinates"]["lat"]),
                    "current_depth_cm": event["currentDepthCm"],
                    "rise_rate_cm_min": event["riseRateCmMin"],
                    "pipe_load_percent": event["pipeLoadPercent"],
                    "risk_level": event["riskLevel"],
                    "started_at": _datetime(event["startedAt"]),
                    "duration_seconds": event.get("durationSeconds"),
                    "camera_id": event.get("cameraId"),
                },
                ["event_id"],
            )
            _upsert(
                session,
                sensors,
                {
                    "sensor_id": sensor.sensorId,
                    "site_id": sensor.siteId,
                    "name": sensor.name,
                    "sensor_type": sensor.sensorType.value,
                    "enabled": sensor.enabled,
                },
                ["sensor_id"],
            )
            _upsert(
                session,
                sensor_flood_mappings,
                {
                    "sensor_id": mapping["sensorId"],
                    "site_id": mapping["siteId"],
                    "flood_point_id": mapping["floodPointId"],
                    "event_id": mapping["eventId"],
                },
                ["sensor_id"],
            )
            for index, frame in enumerate(forecast["frames"]):
                _upsert(
                    session,
                    forecast_frames,
                    {
                        "event_id": forecast["eventId"],
                        "time_key": frame["timeKey"],
                        "generated_at": _datetime(forecast["generatedAt"]),
                        "offset_minutes": frame["offsetMinutes"],
                        "max_depth_cm": frame["maxDepthCm"],
                        "affected_area_km2": frame["affectedAreaKm2"],
                        "geometry_url": frame["geometryUrl"],
                        "geom": _multipolygon(index),
                    },
                    ["event_id", "time_key"],
                )

    return {
        "sites": 1,
        "sensors": 1,
        "flood_points": 1,
        "flood_events": 1,
        "cameras": 1,
        "sensor_flood_mappings": 1,
        "forecast_frames": len(forecast["frames"]),
    }


def _upsert(session: Session, table: Any, values: dict[str, Any], conflict_columns: list[str]) -> None:
    statement = pg_insert(table).values(values)
    update_columns = [key for key in values if key not in conflict_columns]
    statement = statement.on_conflict_do_update(
        index_elements=conflict_columns,
        set_={key: getattr(statement.excluded, key) for key in update_columns},
    )
    session.execute(statement)


def _point(lon: float, lat: float) -> Any:
    return func.ST_SetSRID(func.ST_Point(float(lon), float(lat)), 4326)


def _multipolygon(index: int) -> Any:
    lon, lat = 121.4874, 31.2297
    size = 0.0006 + index * 0.0002
    coordinates = [
        (lon - size, lat - size),
        (lon + size, lat - size),
        (lon + size, lat + size),
        (lon - size, lat + size),
        (lon - size, lat - size),
    ]
    ring = ", ".join(f"{x} {y}" for x, y in coordinates)
    return func.ST_GeomFromText(f"MULTIPOLYGON ((({ring})))", 4326)


def _datetime(value: str) -> datetime:
    return datetime.fromisoformat(value)
