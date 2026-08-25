from __future__ import annotations

from datetime import datetime, timezone

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import FileResponse

from .models import (
    AIAnalysis,
    Camera,
    DashboardOverview,
    FloodEvent,
    FloodForecast,
    FloodPoint,
    MeteorologyContext,
    RainfallSnapshot,
    RainfallStationRankingItem,
    ScenarioTimeline,
    ShanghaiWaterSnapshot,
    SensorState,
    TelemetryObservation,
    VisionDepthObservation,
    VisionDepthUrlRequest,
)
from .config import load_settings
from .repository import UnknownSensorError, build_repository
from .meteorology import MeteorologyContextService, MeteorologyError
from .shanghai_water import ShanghaiWaterAdapter, ShanghaiWaterError
from .vision_depth import VisionDepthAdapter, VisionDepthError


app = FastAPI(
    title="Shanshui Waterlogging MVP API",
    version="0.1.0",
    description="Contract smoke with memory default and optional PostgreSQL/PostGIS persistence.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

settings = load_settings()
repository = build_repository(settings)
# Kept as a compatibility name for the existing smoke and local integrations.
sensor_repository = repository
realtime_clients: set[WebSocket] = set()
SENSOR_SOURCE = "DEMO_DEVICE"
vision_depth_adapter = VisionDepthAdapter()
shanghai_water_adapter = ShanghaiWaterAdapter(
    timeout_seconds=settings.shanghai_water_timeout_seconds,
    cache_ttl_seconds=settings.shanghai_water_cache_ttl_seconds,
)
meteorology_context_service = MeteorologyContextService(shanghai_water_adapter)


def not_found(resource: str, identifier: str) -> HTTPException:
    return HTTPException(
        status_code=404,
        detail={
            "code": "NOT_FOUND",
            "resource": resource,
            "id": identifier,
            "message": f"{resource} '{identifier}' was not found",
        },
    )


def vision_error(error: VisionDepthError) -> HTTPException:
    return HTTPException(status_code=error.status_code, detail=error.detail())


@app.get("/api/v1/dashboard/overview", response_model=DashboardOverview, operation_id="getDashboardOverview")
def get_dashboard_overview() -> DashboardOverview:
    return repository.dashboard_overview


@app.get("/api/v1/rainfall/current", response_model=RainfallSnapshot, operation_id="getCurrentRainfall")
def get_current_rainfall() -> RainfallSnapshot:
    return repository.rainfall


@app.get(
    "/api/v1/rainfall/stations/ranking",
    response_model=list[RainfallStationRankingItem],
    operation_id="listRainfallStationRanking",
)
def list_rainfall_station_ranking() -> list[RainfallStationRankingItem]:
    return repository.list_rainfall_station_ranking()


@app.get(
    "/api/v1/external/shanghai-water",
    response_model=ShanghaiWaterSnapshot,
    operation_id="getShanghaiWaterSnapshot",
    tags=["provisional-external-source"],
    include_in_schema=False,
)
def get_shanghai_water_snapshot() -> ShanghaiWaterSnapshot:
    if settings.data_mode == "fixture":
        raise HTTPException(
            status_code=503,
            detail={
                "code": "REAL_SOURCE_DISABLED",
                "message": "Set DATA_MODE=hybrid or DATA_MODE=real to enable the Shanghai Water Bureau adapter",
            },
        )
    try:
        return shanghai_water_adapter.fetch(allow_partial=settings.data_mode == "hybrid")
    except ShanghaiWaterError as exc:
        raise HTTPException(status_code=503, detail={"code": exc.code, "message": exc.message}) from exc


@app.get(
    "/api/v1/context/meteorology",
    response_model=MeteorologyContext,
    operation_id="getMeteorologyContext",
    tags=["provisional-context"],
    include_in_schema=False,
)
def get_meteorology_context() -> MeteorologyContext:
    try:
        return meteorology_context_service.get(settings.data_mode)
    except MeteorologyError as exc:
        raise HTTPException(status_code=503, detail={"code": exc.code, "message": exc.message}) from exc


@app.get("/api/v1/flood-points", response_model=list[FloodPoint], operation_id="listFloodPoints")
def list_flood_points() -> list[FloodPoint]:
    return repository.list_flood_points()


@app.get("/api/v1/flood-events/{event_id}", response_model=FloodEvent, operation_id="getFloodEvent")
def get_flood_event(event_id: str) -> FloodEvent:
    event = repository.get_event(event_id)
    if event is None:
        raise not_found("flood-event", event_id)
    return event


@app.get(
    "/api/v1/flood-events/{event_id}/forecast",
    response_model=FloodForecast,
    operation_id="getFloodForecast",
)
def get_flood_forecast(event_id: str) -> FloodForecast:
    if repository.get_event(event_id) is None:
        raise not_found("flood-event", event_id)
    forecast = repository.get_forecast(event_id)
    if forecast is None:
        raise not_found("forecast", event_id)
    return forecast


@app.get(
    "/api/v1/flood-events/{event_id}/analysis",
    response_model=AIAnalysis,
    operation_id="getFloodAnalysis",
)
def get_flood_analysis(event_id: str) -> AIAnalysis:
    if repository.get_event(event_id) is None:
        raise not_found("flood-event", event_id)
    analysis = repository.get_analysis(event_id)
    if analysis is None:
        raise not_found("analysis", event_id)
    return analysis


@app.get("/api/v1/cameras", response_model=list[Camera], operation_id="listCameras")
def list_cameras() -> list[Camera]:
    return repository.list_cameras()


@app.get("/api/v1/cameras/{camera_id}", response_model=Camera, operation_id="getCamera")
def get_camera(camera_id: str) -> Camera:
    camera = repository.get_camera(camera_id)
    if camera is None:
        raise not_found("camera", camera_id)
    return camera


@app.get(
    "/api/v1/scenarios/{scenario_id}/timeline",
    response_model=ScenarioTimeline,
    operation_id="getScenarioTimeline",
)
def get_scenario_timeline(scenario_id: str) -> ScenarioTimeline:
    timeline = repository.get_timeline(scenario_id)
    if timeline is None:
        raise not_found("scenario", scenario_id)
    return timeline


async def broadcast_sensor_updated(state: SensorState) -> None:
    envelope = {
        "type": "sensor.updated",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": state.model_dump(mode="json", exclude_none=True),
    }
    disconnected: list[WebSocket] = []
    for client in tuple(realtime_clients):
        try:
            await client.send_json(envelope)
        except Exception:
            disconnected.append(client)
    for client in disconnected:
        realtime_clients.discard(client)


@app.post(
    "/api/v1/telemetry/observations",
    response_model=SensorState,
    response_model_exclude_none=True,
    status_code=201,
    operation_id="createTelemetryObservation",
)
async def post_telemetry_observation(payload: TelemetryObservation) -> SensorState:
    try:
        state = repository.record_observation(
            payload,
            received_at=datetime.now(timezone.utc),
            source=SENSOR_SOURCE,
        )
    except UnknownSensorError:
        raise not_found("sensor", payload.sensorId)
    await broadcast_sensor_updated(state)
    return state


@app.post(
    "/api/v1/vision-depth/analyze/upload",
    response_model=VisionDepthObservation,
    operation_id="analyzeVisionDepthUpload",
    responses={
        400: {"description": "Invalid image input"},
        413: {"description": "Image too large"},
        415: {"description": "Unsupported media type"},
    },
)
async def analyze_vision_depth_upload(
    file: UploadFile = File(...),
    imageId: str | None = Form(default=None),
) -> VisionDepthObservation:
    try:
        return await vision_depth_adapter.analyze_upload(file, imageId)
    except VisionDepthError as exc:
        raise vision_error(exc) from exc


@app.post(
    "/api/v1/vision-depth/analyze/url",
    response_model=VisionDepthObservation,
    operation_id="analyzeVisionDepthUrl",
    responses={
        400: {"description": "Invalid image URL or media"},
        502: {"description": "Image fetch or inference failure"},
    },
)
def analyze_vision_depth_url(payload: VisionDepthUrlRequest) -> VisionDepthObservation:
    try:
        return vision_depth_adapter.analyze_url(payload.url, payload.imageId)
    except VisionDepthError as exc:
        raise vision_error(exc) from exc


@app.get("/api/v1/vision-depth/artifacts/{filename}", include_in_schema=False)
def get_vision_depth_artifact(filename: str) -> FileResponse:
    try:
        artifact = vision_depth_adapter.artifact_path(filename)
    except VisionDepthError as exc:
        raise vision_error(exc) from exc
    return FileResponse(artifact, media_type="image/png")


@app.get(
    "/api/v1/sensors/{sensor_id}",
    response_model=SensorState,
    response_model_exclude_none=True,
    operation_id="getSensorState",
)
def get_sensor_state(sensor_id: str) -> SensorState:
    sensor = repository.get_entry(sensor_id)
    if sensor is None:
        raise not_found("sensor", sensor_id)
    state = repository.get_state(sensor_id)
    if state is None:
        raise not_found("sensor-state", sensor_id)
    return state


@app.websocket("/ws/v1/realtime")
async def realtime_stub(websocket: WebSocket) -> None:
    """Scenario stub plus in-memory sensor.updated broadcasts."""
    await websocket.accept()
    try:
        await websocket.send_json(
            {
                "type": "scenario.started",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "payload": {"scenarioId": "SHANGHAI-DEMO-001"},
            }
        )
        realtime_clients.add(websocket)
        while True:
            message = await websocket.receive()
            if message["type"] == "websocket.disconnect":
                return
    except WebSocketDisconnect:
        return
    finally:
        realtime_clients.discard(websocket)


def _contract_openapi() -> dict:
    """Keep FastAPI's multipart operation aligned with the frozen Contract name."""

    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(title=app.title, version=app.version, description=app.description, routes=app.routes)
    components = schema.setdefault("components", {}).setdefault("schemas", {})
    components["VisionDepthUploadRequest"] = {
        "type": "object",
        "required": ["file"],
        "properties": {
            "file": {"type": "string", "format": "binary"},
            "imageId": {"type": "string"},
        },
    }
    components.pop("Body_analyzeVisionDepthUpload", None)
    schema["paths"]["/api/v1/vision-depth/analyze/upload"]["post"]["requestBody"] = {
        "required": True,
        "content": {
            "multipart/form-data": {
                "schema": {"$ref": "#/components/schemas/VisionDepthUploadRequest"}
            }
        },
    }
    app.openapi_schema = schema
    return schema


app.openapi = _contract_openapi
