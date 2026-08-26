from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Literal

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


class WaterloggingDisposition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pending: int = Field(ge=0)
    handling: int = Field(ge=0)
    relieved: int = Field(ge=0)


class WaterloggingDistrict(BaseModel):
    model_config = ConfigDict(extra="forbid")

    district: str = Field(min_length=1)
    eventCount: int = Field(ge=0)


class WaterloggingMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    maxDepthCm: float = Field(ge=0)
    avgDepthCm: float = Field(ge=0)
    avgResponseMinutes: float = Field(ge=0)
    newToday: int = Field(ge=0)


class WaterloggingSituation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    totalEvents: int = Field(ge=0)
    changeVsHour: float
    disposition: WaterloggingDisposition
    topDistricts: list[WaterloggingDistrict]
    metrics: WaterloggingMetrics
    source: str = Field(min_length=1)


class DashboardOverview(BaseModel):
    updatedAt: datetime
    city: str
    weather: Weather
    urbanStatus: UrbanStatus
    activeFloodPoints: int
    waterloggingSituation: WaterloggingSituation | None = None


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


class ShanghaiWaterSourceStatus(str, Enum):
    OK = "ok"
    SCHEMA_MISMATCH = "schema_mismatch"
    UNAVAILABLE = "unavailable"
    EMPTY = "empty"


class ShanghaiWaterSourceHealth(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: ShanghaiWaterSourceStatus
    sourceUrl: str
    recordCount: int = Field(ge=0)
    observedLatestAt: datetime | None = None
    fetchedAt: datetime | None = None
    errorCode: str | None = None
    synthetic: bool = False
    fallbackReason: str | None = None


class ShanghaiWaterRainfallStation(BaseModel):
    """Raw, source-labelled rainfall value from the Shanghai Water Bureau page."""

    model_config = ConfigDict(extra="forbid")

    stationId: str
    sourceId: str
    stationName: str
    district: str | None = None
    township: str | None = None
    coordinates: Coordinates
    rainfallValue: float = Field(ge=0)
    observedAt: datetime
    receivedAt: datetime
    provider: str
    synthetic: bool = False
    rawSource: str
    dataSource: str | None = None
    isRaining: bool | None = None


class ShanghaiWaterPondingSite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    siteId: str
    sourceId: str
    siteName: str
    district: str | None = None
    coordinates: Coordinates
    depthCm: float = Field(ge=0)
    observedAt: datetime
    receivedAt: datetime
    provider: str
    synthetic: bool = False
    rawSource: str
    stage: str | None = None
    state: str | None = None
    dataSource: str | None = None


class ShanghaiWaterLevelStation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stationId: str
    sourceId: str
    stationName: str
    district: str | None = None
    river: str | None = None
    coordinates: Coordinates
    outWaterM: float
    observedAt: datetime
    receivedAt: datetime
    provider: str
    synthetic: bool = False
    rawSource: str
    dataSource: str | None = None


class ShanghaiWaterLevelForecast(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stationId: str
    sourceId: str
    stationName: str
    coordinates: Coordinates
    forecastWaterLevelM: float
    forecastAt: datetime
    receivedAt: datetime
    provider: str
    synthetic: bool = False
    rawSource: str


class ShanghaiWaterSnapshot(BaseModel):
    """Provisional external-source response; formal Contract fixtures stay unchanged."""

    model_config = ConfigDict(extra="forbid")

    source: str
    fetchedAt: datetime
    receivedAt: datetime
    sourceStatus: str
    sourceHealth: dict[str, ShanghaiWaterSourceHealth]
    coordinateReference: str
    sourceUrls: list[str] = Field(min_length=1)
    rainfall: list[ShanghaiWaterRainfallStation]
    ponding: list[ShanghaiWaterPondingSite]
    waterLevels: list[ShanghaiWaterLevelStation]
    waterLevelForecast: list[ShanghaiWaterLevelForecast]
    synthetic: bool = False
    fallbackReason: str | None = None
    cacheHit: bool = False


class ShanghaiWaterRainfallHistoryPoint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stationId: str
    stationName: str
    observedAt: datetime
    rainfallValue: float = Field(ge=0)


class ShanghaiWaterRealtimeStatus(str, Enum):
    DISABLED = "disabled"
    LOADING = "loading"
    READY = "ready"
    DEGRADED = "degraded"


class ShanghaiWaterRealtimeState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: ShanghaiWaterRealtimeStatus
    pollIntervalSeconds: float = Field(gt=0)
    polledAt: datetime | None = None
    lastSuccessfulPollAt: datetime | None = None
    sourceChangedAt: datetime | None = None
    sourceChangedThisPoll: bool = False
    rainfallChangedThisPoll: bool = False
    latestSourceObservedAt: datetime | None = None
    consecutiveFailures: int = Field(default=0, ge=0)
    lastError: str | None = None
    snapshot: ShanghaiWaterSnapshot | None = None
    rainfallHistory: dict[str, list[ShanghaiWaterRainfallHistoryPoint]] = Field(default_factory=dict)


class MeteorologyMode(str, Enum):
    FIXTURE = "fixture"
    HYBRID = "hybrid"
    REAL = "real"


class MeteorologyDataStatus(str, Enum):
    REAL = "REAL"
    MIXED = "MIXED"
    SYNTHETIC = "SYNTHETIC"
    DEGRADED = "DEGRADED"


class MeteorologySourceHealthStatus(str, Enum):
    OK = "OK"
    SYNTHETIC = "SYNTHETIC"
    UNAVAILABLE = "UNAVAILABLE"
    NOT_VERIFIED = "NOT_VERIFIED"
    AUTH_REQUIRED = "AUTH_REQUIRED"
    SCHEMA_MISMATCH = "SCHEMA_MISMATCH"
    TIMEOUT = "TIMEOUT"


class MeteorologyWarning(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str
    level: str
    issuedAt: datetime
    expiresAt: datetime | None = None
    sourceId: str
    area: str | None = None
    synthetic: bool = False


class MeteorologyRainfallStation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stationId: str | None = None
    stationName: str
    district: str | None = None
    coordinates: Coordinates | None = None
    coordinateReference: str | None = None
    rainfallValue: float = Field(ge=0)
    unit: str = "mm"
    windowMinutes: int | None = Field(default=None, ge=0)
    observedAt: datetime
    sourceId: str
    synthetic: bool = False


class MeteorologyRainfallNow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stations: list[MeteorologyRainfallStation]


class MeteorologyNowcastFrame(BaseModel):
    model_config = ConfigDict(extra="forbid")

    offsetMinutes: Literal[0, 30, 60, 120]
    validAt: datetime
    rasterUrl: str | None = None
    previewUrl: str | None = None
    mediaType: str | None = None
    crs: str | None = None
    bbox: list[float] | None = Field(default=None, min_length=4, max_length=4)
    georeferenced: bool = False
    renderableInCesium: bool = False
    sourceId: str
    synthetic: bool = False


class MeteorologyNowcast(BaseModel):
    model_config = ConfigDict(extra="forbid")

    frames: list[MeteorologyNowcastFrame]


class MeteorologySourceHealth(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str
    sourceId: str
    status: MeteorologySourceHealthStatus
    observedAt: datetime | None = None
    receivedAt: datetime
    message: str | None = None


class MeteorologyContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    observedAt: datetime | None = None
    receivedAt: datetime
    source: str
    coordinateReference: str | None = None
    mode: MeteorologyMode
    dataStatus: MeteorologyDataStatus
    warnings: list[MeteorologyWarning]
    rainfallNow: MeteorologyRainfallNow
    nowcast: MeteorologyNowcast
    sourceHealth: list[MeteorologySourceHealth]


class FloodPoint(BaseModel):
    id: str
    name: str
    district: str | None = None
    coordinates: Coordinates
    depthCm: float
    riskLevel: RiskLevel
    trend: Trend
    eventId: str | None = None
    sensorId: str | None = None


class HistoricalCaseMedia(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sourceType: Literal["CASE_SOURCE_MEDIA"]
    sourcePage: str = Field(min_length=1)
    urls: list[str] = Field(min_length=1)
    mvpUseStatus: Literal["APPROVED_LOCAL_MVP"]


class HistoricalFloodCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidateId: str
    incidentDate: str
    reportDate: str
    district: str
    locationText: str
    sourceAgency: str
    sourceTitle: str
    sourceUrl: str
    confirmedFacts: str
    depthCm: float | None = None
    depthEvidenceText: str | None = None
    trafficImpact: str | None = None
    officialActions: list[str]
    evidenceLevel: Literal["OFFICIAL_EXACT", "OFFICIAL_AREA_ONLY", "MEDIA_CORROBORATED", "INSUFFICIENT"]
    sourceType: Literal["PUBLIC_REPORT"]
    dataStatus: Literal["HISTORICAL_PUBLIC_REPORT"]
    mvpReviewStatus: Literal["VERIFIED_FOR_MVP"]
    media: HistoricalCaseMedia | None = None
    countedInRealtime: Literal[False] = False
    floodPointId: str | None = None
    sensorId: Literal[None] = None
    forecast: Literal[None] = None
    liveCamera: Literal[None] = None
    coordinates: Coordinates | None = None


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


class VisionDecisionTrafficStatus(str, Enum):
    NORMAL = "NORMAL"
    CAUTION = "CAUTION"
    NOT_RECOMMENDED = "NOT_RECOMMENDED"
    PROHIBITED = "PROHIBITED"


class VisionDecisionProjection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    floodDetected: bool
    decisionDepthCm: float | None = Field(ge=0)
    trafficStatus: VisionDecisionTrafficStatus
    recommendation: str = Field(min_length=1)


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
    approximateDepthCm: float | None = Field(default=None, ge=0)
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
    decision: VisionDecisionProjection | None = None


class VisionDepthUrlRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    url: str = Field(min_length=1, json_schema_extra={"format": "uri"})
    imageId: str | None = None
