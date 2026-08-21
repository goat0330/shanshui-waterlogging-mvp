from __future__ import annotations

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Identity,
    Integer,
    MetaData,
    String,
    Table,
)
from geoalchemy2 import Geometry


metadata = MetaData()

sites = Table(
    "sites",
    metadata,
    Column("site_id", String(64), primary_key=True),
    Column("name", String(255), nullable=False),
    Column("geom", Geometry("POINT", srid=4326, spatial_index=False), nullable=False),
)

flood_points = Table(
    "flood_points",
    metadata,
    Column("point_id", String(64), primary_key=True),
    Column("name", String(255), nullable=False),
    Column("district", String(128), nullable=True),
    Column("geom", Geometry("POINT", srid=4326, spatial_index=False), nullable=False),
    Column("depth_cm", Float, nullable=False),
    Column("risk_level", String(16), nullable=False),
    Column("trend", String(16), nullable=False),
)

cameras = Table(
    "cameras",
    metadata,
    Column("camera_id", String(64), primary_key=True),
    Column("name", String(255), nullable=False),
    Column("geom", Geometry("POINT", srid=4326, spatial_index=False), nullable=False),
    Column("status", String(16), nullable=False),
    Column("media_type", String(16), nullable=False),
    Column("media_url", String(1024), nullable=False),
    Column("overlay_url", String(1024), nullable=True),
)

flood_events = Table(
    "flood_events",
    metadata,
    Column("event_id", String(64), primary_key=True),
    Column("name", String(255), nullable=False),
    Column("district", String(128), nullable=False),
    Column("event_type", String(128), nullable=False),
    Column("geom", Geometry("POINT", srid=4326, spatial_index=False), nullable=False),
    Column("current_depth_cm", Float, nullable=False),
    Column("rise_rate_cm_min", Float, nullable=False),
    Column("pipe_load_percent", Float, nullable=False),
    Column("risk_level", String(16), nullable=False),
    Column("started_at", DateTime(timezone=True), nullable=False),
    Column("duration_seconds", Integer, nullable=True),
    Column("camera_id", String(64), ForeignKey("cameras.camera_id"), nullable=True),
)

sensors = Table(
    "sensors",
    metadata,
    Column("sensor_id", String(64), primary_key=True),
    Column("site_id", String(64), ForeignKey("sites.site_id"), nullable=False),
    Column("name", String(255), nullable=False),
    Column("sensor_type", String(32), nullable=False),
    Column("enabled", Boolean, nullable=False, server_default="true"),
)

sensor_observations = Table(
    "sensor_observations",
    metadata,
    Column("id", BigInteger, Identity(), primary_key=True),
    Column("sensor_id", String(64), ForeignKey("sensors.sensor_id"), nullable=False),
    Column("observed_at", DateTime(timezone=True), nullable=False),
    Column("received_at", DateTime(timezone=True), nullable=False),
    Column("depth_mm", Float, nullable=False),
    Column("depth_cm", Float, nullable=False),
    Column("water_detected", Boolean, nullable=False),
    Column("sequence", Integer, nullable=True),
    Column("transport", String(32), nullable=True),
    Column("battery_mv", Integer, nullable=True),
    Column("signal_dbm", Float, nullable=True),
    Column("source", String(64), nullable=True),
)

sensor_latest_state = Table(
    "sensor_latest_state",
    metadata,
    Column("sensor_id", String(64), ForeignKey("sensors.sensor_id"), primary_key=True),
    Column("site_id", String(64), ForeignKey("sites.site_id"), nullable=False),
    Column("observed_at", DateTime(timezone=True), nullable=False),
    Column("received_at", DateTime(timezone=True), nullable=False),
    Column("depth_mm", Float, nullable=False),
    Column("depth_cm", Float, nullable=False),
    Column("water_detected", Boolean, nullable=False),
    Column("sequence", Integer, nullable=True),
    Column("transport", String(32), nullable=True),
    Column("battery_mv", Integer, nullable=True),
    Column("signal_dbm", Float, nullable=True),
    Column("source", String(64), nullable=True),
)

sensor_flood_mappings = Table(
    "sensor_flood_mappings",
    metadata,
    Column("sensor_id", String(64), ForeignKey("sensors.sensor_id"), primary_key=True),
    Column("site_id", String(64), ForeignKey("sites.site_id"), nullable=False),
    Column("flood_point_id", String(64), ForeignKey("flood_points.point_id"), nullable=False),
    Column("event_id", String(64), ForeignKey("flood_events.event_id"), nullable=False),
)

forecast_frames = Table(
    "forecast_frames",
    metadata,
    Column("event_id", String(64), ForeignKey("flood_events.event_id"), primary_key=True),
    Column("time_key", String(16), primary_key=True),
    Column("generated_at", DateTime(timezone=True), nullable=False),
    Column("offset_minutes", Integer, nullable=False),
    Column("max_depth_cm", Float, nullable=False),
    Column("affected_area_km2", Float, nullable=False),
    Column("geometry_url", String(1024), nullable=False),
    Column("geom", Geometry("MULTIPOLYGON", srid=4326, spatial_index=False), nullable=False),
)
