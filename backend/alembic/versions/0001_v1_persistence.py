"""V1 PostgreSQL/PostGIS persistence tables.

Revision ID: 0001_v1_persistence
Revises:
Create Date: 2026-08-21
"""

from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geometry


revision = "0001_v1_persistence"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    op.create_table(
        "sites",
        sa.Column("site_id", sa.String(64), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("geom", Geometry("POINT", srid=4326, spatial_index=False), nullable=False),
    )
    op.create_table(
        "flood_points",
        sa.Column("point_id", sa.String(64), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("district", sa.String(128), nullable=True),
        sa.Column("geom", Geometry("POINT", srid=4326, spatial_index=False), nullable=False),
        sa.Column("depth_cm", sa.Float, nullable=False),
        sa.Column("risk_level", sa.String(16), nullable=False),
        sa.Column("trend", sa.String(16), nullable=False),
    )
    op.create_table(
        "cameras",
        sa.Column("camera_id", sa.String(64), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("geom", Geometry("POINT", srid=4326, spatial_index=False), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("media_type", sa.String(16), nullable=False),
        sa.Column("media_url", sa.String(1024), nullable=False),
        sa.Column("overlay_url", sa.String(1024), nullable=True),
    )
    op.create_table(
        "flood_events",
        sa.Column("event_id", sa.String(64), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("district", sa.String(128), nullable=False),
        sa.Column("event_type", sa.String(128), nullable=False),
        sa.Column("geom", Geometry("POINT", srid=4326, spatial_index=False), nullable=False),
        sa.Column("current_depth_cm", sa.Float, nullable=False),
        sa.Column("rise_rate_cm_min", sa.Float, nullable=False),
        sa.Column("pipe_load_percent", sa.Float, nullable=False),
        sa.Column("risk_level", sa.String(16), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_seconds", sa.Integer, nullable=True),
        sa.Column("camera_id", sa.String(64), sa.ForeignKey("cameras.camera_id"), nullable=True),
    )
    op.create_table(
        "sensors",
        sa.Column("sensor_id", sa.String(64), primary_key=True),
        sa.Column("site_id", sa.String(64), sa.ForeignKey("sites.site_id"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("sensor_type", sa.String(32), nullable=False),
        sa.Column("enabled", sa.Boolean, server_default=sa.text("true"), nullable=False),
    )
    op.create_table(
        "sensor_observations",
        sa.Column("id", sa.BigInteger, sa.Identity(), primary_key=True),
        sa.Column("sensor_id", sa.String(64), sa.ForeignKey("sensors.sensor_id"), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("depth_mm", sa.Float, nullable=False),
        sa.Column("depth_cm", sa.Float, nullable=False),
        sa.Column("water_detected", sa.Boolean, nullable=False),
        sa.Column("sequence", sa.Integer, nullable=True),
        sa.Column("transport", sa.String(32), nullable=True),
        sa.Column("battery_mv", sa.Integer, nullable=True),
        sa.Column("signal_dbm", sa.Float, nullable=True),
        sa.Column("source", sa.String(64), nullable=True),
    )
    op.create_table(
        "sensor_latest_state",
        sa.Column("sensor_id", sa.String(64), sa.ForeignKey("sensors.sensor_id"), primary_key=True),
        sa.Column("site_id", sa.String(64), sa.ForeignKey("sites.site_id"), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("depth_mm", sa.Float, nullable=False),
        sa.Column("depth_cm", sa.Float, nullable=False),
        sa.Column("water_detected", sa.Boolean, nullable=False),
        sa.Column("sequence", sa.Integer, nullable=True),
        sa.Column("transport", sa.String(32), nullable=True),
        sa.Column("battery_mv", sa.Integer, nullable=True),
        sa.Column("signal_dbm", sa.Float, nullable=True),
        sa.Column("source", sa.String(64), nullable=True),
    )
    op.create_table(
        "sensor_flood_mappings",
        sa.Column("sensor_id", sa.String(64), sa.ForeignKey("sensors.sensor_id"), primary_key=True),
        sa.Column("site_id", sa.String(64), sa.ForeignKey("sites.site_id"), nullable=False),
        sa.Column("flood_point_id", sa.String(64), sa.ForeignKey("flood_points.point_id"), nullable=False),
        sa.Column("event_id", sa.String(64), sa.ForeignKey("flood_events.event_id"), nullable=False),
    )
    op.create_table(
        "forecast_frames",
        sa.Column("event_id", sa.String(64), sa.ForeignKey("flood_events.event_id"), primary_key=True),
        sa.Column("time_key", sa.String(16), primary_key=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("offset_minutes", sa.Integer, nullable=False),
        sa.Column("max_depth_cm", sa.Float, nullable=False),
        sa.Column("affected_area_km2", sa.Float, nullable=False),
        sa.Column("geometry_url", sa.String(1024), nullable=False),
        sa.Column(
            "geom",
            Geometry("MULTIPOLYGON", srid=4326, spatial_index=False),
            nullable=False,
        ),
    )

    for table_name in ("sites", "flood_points", "cameras", "flood_events", "forecast_frames"):
        op.create_index(
            f"ix_{table_name}_geom",
            table_name,
            ["geom"],
            unique=False,
            postgresql_using="gist",
        )


def downgrade() -> None:
    for table_name in ("sites", "flood_points", "cameras", "flood_events", "forecast_frames"):
        op.drop_index(f"ix_{table_name}_geom", table_name=table_name)
    op.drop_table("forecast_frames")
    op.drop_table("sensor_flood_mappings")
    op.drop_table("sensor_latest_state")
    op.drop_table("sensor_observations")
    op.drop_table("sensors")
    op.drop_table("flood_events")
    op.drop_table("cameras")
    op.drop_table("flood_points")
    op.drop_table("sites")
    op.execute("DROP EXTENSION IF EXISTS postgis")
