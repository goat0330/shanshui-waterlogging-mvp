import type {
  AIAnalysis,
  Camera,
  DashboardDataClient,
  DashboardOverview,
  FloodEvent,
  FloodForecast,
  FloodPoint,
  HistoricalFloodCase,
  MeteorologyContext,
  MeteorologyRealtimeState,
  RainfallSnapshot,
  RainfallStationRankingItem,
  ScenarioTimeline,
  ShanghaiWaterRealtimeState,
  ShanghaiWaterSnapshot,
  SensorState,
} from '../types'

export type DataSource = 'fixture' | 'api'

export const DATA_SOURCE: DataSource = import.meta.env.VITE_DATA_SOURCE === 'api' ? 'api' : 'fixture'
const configuredApiBase = import.meta.env.VITE_API_BASE_URL?.trim() ?? ''
export const API_BASE_URL = configuredApiBase.replace(/\/+$/, '')

function apiUrl(path: string): string {
  return API_BASE_URL ? `${API_BASE_URL}${path}` : path
}

async function requestJson<T>(path: string): Promise<T> {
  const response = await fetch(apiUrl(path), { cache: 'no-store' })
  if (!response.ok) throw new Error(`API ${response.status} ${path}`)
  return response.json() as Promise<T>
}

export const apiClient: DashboardDataClient = {
  getOverview: () => requestJson<DashboardOverview>('/api/v1/dashboard/overview'),
  getRainfall: () => requestJson<RainfallSnapshot>('/api/v1/rainfall/current'),
  getRainfallStationRanking: () => requestJson<RainfallStationRankingItem[]>('/api/v1/rainfall/stations/ranking'),
  listFloodPoints: () => requestJson<FloodPoint[]>('/api/v1/flood-points'),
  listHistoricalCases: () => requestJson<HistoricalFloodCase[]>('/api/v1/historical-cases'),
  getFloodEvent: (eventId: string) => requestJson<FloodEvent>(`/api/v1/flood-events/${encodeURIComponent(eventId)}`),
  getFloodForecast: (eventId: string) => requestJson<FloodForecast>(`/api/v1/flood-events/${encodeURIComponent(eventId)}/forecast`),
  getFloodAnalysis: (eventId: string) => requestJson<AIAnalysis>(`/api/v1/flood-events/${encodeURIComponent(eventId)}/analysis`),
  listCameras: () => requestJson<Camera[]>('/api/v1/cameras'),
  getCamera: (cameraId: string) => requestJson<Camera>(`/api/v1/cameras/${encodeURIComponent(cameraId)}`),
  getSensorState: (sensorId: string) => requestJson<SensorState>(`/api/v1/sensors/${encodeURIComponent(sensorId)}`),
  getTimeline: (scenarioId: string) => requestJson<ScenarioTimeline>(`/api/v1/scenarios/${encodeURIComponent(scenarioId)}/timeline`),
  getShanghaiWater: () => requestJson<ShanghaiWaterSnapshot>('/api/v1/external/shanghai-water').catch(() => null),
  getShanghaiWaterRuntime: () => requestJson<ShanghaiWaterRealtimeState>('/api/v1/external/shanghai-water/runtime').catch(() => null),
  getMeteorology: () => requestJson<MeteorologyContext>('/api/v1/context/meteorology').catch(() => null),
  getMeteorologyRuntime: () => requestJson<MeteorologyRealtimeState>('/api/v1/context/meteorology/runtime').catch(() => null),
}

export function getRealtimeUrl(baseUrl = API_BASE_URL): string {
  const base = baseUrl || window.location.origin
  const url = new URL(base, window.location.origin)
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
  url.pathname = `${url.pathname.replace(/\/$/, '')}/ws/v1/realtime`
  url.search = ''
  return url.toString()
}
