from __future__ import annotations

from datetime import datetime
from enum import Enum

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
