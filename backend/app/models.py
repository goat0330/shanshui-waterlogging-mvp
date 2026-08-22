from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RiskLevel(str, Enum):
    NORMAL = "NORMAL"
    WARNING = "WARNING"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Trend(str, Enum):
    UP = "UP"
    STABLE = "STABLE"
    DOWN = "DOWN"


class Coordinates(BaseModel):
    lat: float
    lon: float


class SensorType(str, Enum):
    WATER_DEPTH = "WATER_DEPTH"


class TelemetryTransport(str, Enum):
    WIFI = "WIFI"
    CELLULAR_4G = "CELLULAR_4G"
    SIMULATOR = "SIMULATOR"


class TelemetryObservation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sensorId: str = Field(min_length=1)
    observedAt: datetime
    depthMm: float = Field(ge=0)
    sequence: int | None = Field(default=None, ge=0)
    transport: TelemetryTransport | None = None
    batteryMv: int | None = Field(default=None, ge=0)
    signalDbm: float | None = None


class SensorState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sensorId: str
    siteId: str
    coordinates: Coordinates
    depthMm: float = Field(ge=0)
    depthCm: float = Field(ge=0)
    waterDetected: bool
    observedAt: datetime
    receivedAt: datetime
    sequence: int | None = Field(default=None, ge=0)
    transport: TelemetryTransport | None = None
    batteryMv: int | None = None
    signalDbm: float | None = None
    source: str | None = None


class SensorRegistryEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sensorId: str
    siteId: str
    name: str
    coordinates: Coordinates
    sensorType: SensorType
    enabled: bool


class Weather(BaseModel):
    temperatureC: float
    condition: str


class UrbanStatus(BaseModel):
    critical: int
    warning: int
    normal: int


class DashboardOverview(BaseModel):
    updatedAt: datetime
    city: str
    weather: Weather
    urbanStatus: UrbanStatus
    activeFloodPoints: int


class RainfallTrendPoint(BaseModel):
    minutesAgo: int
    valueMmH: float


class RainfallSnapshot(BaseModel):
    updatedAt: datetime
    intensityMmH: float
    cumulativeMm: float
    durationMinutes: int
    trend: list[RainfallTrendPoint]


class RainfallStationRankingItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stationId: str
    stationName: str
    intensityMmH: float = Field(ge=0)


class FloodPoint(BaseModel):
    id: str
    name: str
    district: str | None = None
    coordinates: Coordinates
    depthCm: float
    riskLevel: RiskLevel
    trend: Trend


class FloodEvent(BaseModel):
    id: str
    name: str
    district: str
    eventType: str
    coordinates: Coordinates
    currentDepthCm: float
    riseRateCmMin: float
    pipeLoadPercent: float
    riskLevel: RiskLevel
    startedAt: datetime
    durationSeconds: int | None = None
    cameraId: str | None = None


class ForecastKey(str, Enum):
    NOW = "NOW"
    PLUS_10 = "PLUS_10"
    PLUS_30 = "PLUS_30"


class ForecastFrame(BaseModel):
    timeKey: ForecastKey
    offsetMinutes: int
    maxDepthCm: float
    affectedAreaKm2: float
    geometryUrl: str


class FloodForecast(BaseModel):
    eventId: str
    generatedAt: datetime
    frames: list[ForecastFrame]


class CameraStatus(str, Enum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"


class MediaType(str, Enum):
    MP4 = "MP4"
    HLS = "HLS"
    WEBRTC = "WEBRTC"


class Camera(BaseModel):
    id: str
    name: str
    coordinates: Coordinates
    status: CameraStatus
    mediaType: MediaType
    mediaUrl: str
    overlayUrl: str | None = None


class AnalysisCause(BaseModel):
    label: str
    weight: float


class AnalysisAction(BaseModel):
    priority: int
    title: str
    detail: str


class AIAnalysis(BaseModel):
    eventId: str
    riskSummary: str
    causes: list[AnalysisCause]
    forecastSummary: str
    actions: list[AnalysisAction]


class ScenarioMode(str, Enum):
    REALTIME = "REALTIME"
    PLAYBACK = "PLAYBACK"
    FORECAST = "FORECAST"


class ScenarioTimeline(BaseModel):
    scenarioId: str
    currentTime: datetime
    mode: ScenarioMode
    selectedForecastKey: ForecastKey | None = None


class VisionDepthMethod(str, Enum):
    VISUAL_RANGE = "VISUAL_RANGE"
    NO_REFERENCE = "NO_REFERENCE"
    PERSON_REFERENCE = "PERSON_REFERENCE"
    VEHICLE_REFERENCE = "VEHICLE_REFERENCE"
    TRAFFIC_SIGN_REFERENCE = "TRAFFIC_SIGN_REFERENCE"
    FIXED_CAMERA_REFERENCE = "FIXED_CAMERA_REFERENCE"


class VisionDepthQuality(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    REJECT = "REJECT"


class VisionDepthSourceType(str, Enum):
    URL = "url"
    LOCAL = "local"


class VisionDepthSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: VisionDepthSourceType
    value: str = Field(min_length=1)


class VisionDepthProvenanceSourceType(str, Enum):
    IMAGE = "VISION_IMAGE"
    VIDEO = "VISION_VIDEO"


class VisionDepthLicenseReview(str, Enum):
    APPROVED = "approved"
    PENDING = "pending"
    NOT_REQUIRED = "not_required"


class VisionDepthRuntimePolicy(str, Enum):
    RESEARCH_MVP = "research_mvp"
    PRODUCTION = "production"


class VisionDepthProvenance(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sourceType: VisionDepthProvenanceSourceType
    sourceId: str = Field(min_length=1)
    observedAt: datetime | None
    licenseReview: VisionDepthLicenseReview
    runtimePolicy: VisionDepthRuntimePolicy


class VisionDepthEstimate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    level: int = Field(ge=0, le=5)
    estimatedDepthCm: float | None = Field(default=None, ge=0)
    rangeCm: list[float | None] = Field(min_length=2, max_length=2)
    confidence: float = Field(ge=0, le=1)


class VisionDepthObservation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    imageId: str
    source: VisionDepthSource
    provenance: VisionDepthProvenance
    floodDetected: bool
    depth: VisionDepthEstimate
    method: VisionDepthMethod
    referenceObjects: list[dict[str, Any]]
    waterMaskPath: str
    quality: VisionDepthQuality
    qualityFlags: list[str]
    model: dict[str, Any]
    synthetic: bool


class VisionDepthUrlRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str = Field(min_length=1, json_schema_extra={"format": "uri"})
    imageId: str | None = None
