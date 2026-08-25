export type RiskLevel = 'NORMAL' | 'WARNING' | 'HIGH' | 'CRITICAL'

export type ForecastKey = 'NOW' | 'PLUS_10' | 'PLUS_30'

export type PanelState = 'ready' | 'loading' | 'empty' | 'error'

export interface Coordinates {
  lat: number
  lon: number
}

export interface WaterloggingSituation {
  totalEvents: number
  changeVsHour: number
  disposition: {
    pending: number
    handling: number
    relieved: number
  }
  topDistricts: Array<{
    district: string
    eventCount: number
  }>
  metrics: {
    maxDepthCm: number
    avgDepthCm: number
    avgResponseMinutes: number
    newToday: number
  }
  source: string
}

export interface DashboardOverview {
  updatedAt: string
  city: string
  weather: {
    temperatureC: number
    condition: string
  }
  urbanStatus: {
    critical: number
    warning: number
    normal: number
  }
  activeFloodPoints: number
  waterloggingSituation?: WaterloggingSituation | null
}

export interface RainfallSnapshot {
  updatedAt: string
  intensityMmH: number
  cumulativeMm: number
  durationMinutes: number
  trend: Array<{
    minutesAgo: number
    valueMmH: number
  }>
}

export interface RainfallStationRankingItem {
  stationId: string
  stationName: string
  intensityMmH: number
}

export interface ShanghaiWaterRainfallStation {
  stationId: string
  stationName: string
  district?: string | null
  township?: string | null
  coordinates: Coordinates
  rainfallValue: number
  observedAt: string
  dataSource?: string | null
  isRaining?: boolean | null
}

export interface ShanghaiWaterPondingSite {
  siteId: string
  siteName: string
  district?: string | null
  coordinates: Coordinates
  depthCm: number
  observedAt: string
  stage?: string | null
  state?: string | null
  dataSource?: string | null
}

export interface ShanghaiWaterLevelStation {
  stationId: string
  stationName: string
  district?: string | null
  river?: string | null
  coordinates: Coordinates
  outWaterM: number
  observedAt: string
  dataSource?: string | null
}

export interface ShanghaiWaterLevelForecast {
  stationId: string
  stationName: string
  coordinates: Coordinates
  forecastWaterLevelM: number
  forecastAt: string
}

export interface ShanghaiWaterSnapshot {
  source: string
  fetchedAt: string
  coordinateReference: string
  sourceUrls: string[]
  rainfall: ShanghaiWaterRainfallStation[]
  ponding: ShanghaiWaterPondingSite[]
  waterLevels: ShanghaiWaterLevelStation[]
  waterLevelForecast: ShanghaiWaterLevelForecast[]
}

export interface FloodPoint {
  id: string
  name: string
  district?: string
  coordinates: Coordinates
  depthCm: number
  riskLevel: RiskLevel
  trend: 'UP' | 'STABLE' | 'DOWN'
  eventId?: string | null
  sensorId?: string | null
}

export interface HistoricalFloodCase {
  candidateId: string
  incidentDate: string
  reportDate: string
  district: string
  locationText: string
  sourceAgency: string
  sourceTitle: string
  sourceUrl: string
  confirmedFacts: string
  depthCm: number | null
  depthEvidenceText: string | null
  trafficImpact: string | null
  officialActions: string[]
  evidenceLevel: 'OFFICIAL_EXACT' | 'OFFICIAL_AREA_ONLY' | 'MEDIA_CORROBORATED' | 'INSUFFICIENT'
  sourceType: 'PUBLIC_REPORT'
  dataStatus: 'HISTORICAL_PUBLIC_REPORT'
  floodPointId: string | null
  sensorId: string | null
  coordinates: Coordinates | null
}

export interface FloodEvent {
  id: string
  name: string
  district: string
  eventType: string
  coordinates: Coordinates
  currentDepthCm: number
  riseRateCmMin: number
  pipeLoadPercent: number
  riskLevel: RiskLevel
  startedAt: string
  durationSeconds?: number
  cameraId?: string
}

export interface ForecastFrame {
  timeKey: ForecastKey
  offsetMinutes: number
  maxDepthCm: number
  affectedAreaKm2: number
  geometryUrl: string
}

export interface FloodForecast {
  eventId: string
  generatedAt: string
  frames: ForecastFrame[]
}

export interface Camera {
  id: string
  name: string
  coordinates: Coordinates
  status: 'ONLINE' | 'OFFLINE'
  mediaType: 'MP4' | 'HLS' | 'WEBRTC'
  mediaUrl: string
  overlayUrl?: string
}

export interface AIAnalysis {
  eventId: string
  riskSummary: string
  causes: Array<{ label: string; weight: number }>
  forecastSummary: string
  actions: Array<{ priority: number; title: string; detail: string }>
}

export interface ScenarioTimeline {
  scenarioId: string
  currentTime: string
  mode: 'REALTIME' | 'PLAYBACK' | 'FORECAST'
  selectedForecastKey?: ForecastKey
}

export interface SensorState {
  sensorId: string
  siteId: string
  coordinates: Coordinates
  depthMm: number
  depthCm: number
  waterDetected: boolean
  observedAt: string
  receivedAt: string
  sequence?: number
  transport?: 'WIFI' | 'CELLULAR_4G' | 'SIMULATOR'
  batteryMv?: number
  signalDbm?: number
  source?: string
}

export interface VisionDepthProvenance {
  sourceType: 'VISION_IMAGE' | 'VISION_VIDEO'
  sourceId: string
  observedAt: string | null
  licenseReview: 'approved' | 'pending' | 'not_required'
  runtimePolicy: 'research_mvp' | 'production'
}

export interface DecisionProjection {
  decisionDepthCm: number | null
  trafficStatus: string
  recommendation: string
}

export interface VisionDepthObservation {
  imageId: string
  source: {
    type: 'url' | 'local'
    value: string
  }
  provenance: VisionDepthProvenance
  floodDetected: boolean
  depth: {
    level: number
    estimatedDepthCm: number | null
    approximateDepthCm?: number | null
    rangeCm: [number | null, number | null]
    confidence: number
  }
  method: 'VISUAL_RANGE' | 'NO_REFERENCE' | 'PERSON_REFERENCE' | 'VEHICLE_REFERENCE' | 'TRAFFIC_SIGN_REFERENCE' | 'FIXED_CAMERA_REFERENCE'
  referenceObjects: Array<Record<string, unknown>>
  waterMaskPath: string
  quality: 'LOW' | 'MEDIUM' | 'HIGH' | 'REJECT'
  qualityFlags: string[]
  model: Record<string, unknown>
  synthetic: boolean
  decision?: DecisionProjection | null
}

export interface SensorFloodPointMapping {
  sensorId: string
  siteId: string
  floodPointId: string
  eventId: string
}

export interface DashboardData {
  overview: DashboardOverview
  rainfall: RainfallSnapshot
  rainfallRanking: RainfallStationRankingItem[]
  points: FloodPoint[]
  historicalCases: HistoricalFloodCase[]
  event: FloodEvent | null
  forecast: FloodForecast | null
  camera: Camera | null
  analysis: AIAnalysis | null
  timeline: ScenarioTimeline
  sensor?: SensorState | null
  shanghaiWater?: ShanghaiWaterSnapshot | null
  eventsById?: Record<string, FloodEvent>
  forecastsByEventId?: Record<string, FloodForecast>
  analysesByEventId?: Record<string, AIAnalysis>
  camerasById?: Record<string, Camera>
  sensorsById?: Record<string, SensorState>
}

export interface DashboardDataClient {
  getOverview(): Promise<DashboardOverview>
  getRainfall(): Promise<RainfallSnapshot>
  getRainfallStationRanking(): Promise<RainfallStationRankingItem[]>
  listFloodPoints(): Promise<FloodPoint[]>
  listHistoricalCases(): Promise<HistoricalFloodCase[]>
  getFloodEvent(eventId: string): Promise<FloodEvent>
  getFloodForecast(eventId: string): Promise<FloodForecast>
  getFloodAnalysis(eventId: string): Promise<AIAnalysis>
  listCameras(): Promise<Camera[]>
  getCamera(cameraId: string): Promise<Camera>
  getSensorState(sensorId: string): Promise<SensorState>
  getTimeline(scenarioId: string): Promise<ScenarioTimeline>
  getShanghaiWater(): Promise<ShanghaiWaterSnapshot | null>
}

export interface HomeFixtures {
  overview: DashboardOverview
  rainfall: RainfallSnapshot
  rainfallRanking: RainfallStationRankingItem[]
  points: FloodPoint[]
  historicalCases: HistoricalFloodCase[]
  event: FloodEvent
  forecast: FloodForecast
  camera: Camera
  analysis: AIAnalysis
  timeline: ScenarioTimeline
  shanghaiWater?: ShanghaiWaterSnapshot | null
}
