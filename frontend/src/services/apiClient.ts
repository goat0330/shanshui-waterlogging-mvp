import type {
  AIAnalysis,
  Camera,
  DashboardDataClient,
  DashboardOverview,
  FloodEvent,
  FloodForecast,
  FloodPoint,
  RainfallSnapshot,
  RainfallStationRankingItem,
  ScenarioTimeline,
  SensorState,
} from '../types'

export type DataSource = 'fixture' | 'api'

export const DATA_SOURCE: DataSource = import.meta.env.VITE_DATA_SOURCE === 'api' ? 'api' : 'fixture'
export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/+$/, '')

async function requestJson<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`)
  if (!response.ok) {
    throw new Error(`API ${response.status} ${path}`)
  }
  return response.json() as Promise<T>
}

export const apiClient: DashboardDataClient = {
  getOverview: () => requestJson<DashboardOverview>('/api/v1/dashboard/overview'),
  getRainfall: () => requestJson<RainfallSnapshot>('/api/v1/rainfall/current'),
  getRainfallStationRanking: () => requestJson<RainfallStationRankingItem[]>('/api/v1/rainfall/stations/ranking'),
  listFloodPoints: () => requestJson<FloodPoint[]>('/api/v1/flood-points'),
  getFloodEvent: (eventId: string) => requestJson<FloodEvent>(`/api/v1/flood-events/${encodeURIComponent(eventId)}`),
  getFloodForecast: (eventId: string) => requestJson<FloodForecast>(`/api/v1/flood-events/${encodeURIComponent(eventId)}/forecast`),
  getFloodAnalysis: (eventId: string) => requestJson<AIAnalysis>(`/api/v1/flood-events/${encodeURIComponent(eventId)}/analysis`),
  listCameras: () => requestJson<Camera[]>('/api/v1/cameras'),
  getCamera: (cameraId: string) => requestJson<Camera>(`/api/v1/cameras/${encodeURIComponent(cameraId)}`),
  getSensorState: (sensorId: string) => requestJson<SensorState>(`/api/v1/sensors/${encodeURIComponent(sensorId)}`),
  getTimeline: (scenarioId: string) => requestJson<ScenarioTimeline>(`/api/v1/scenarios/${encodeURIComponent(scenarioId)}/timeline`),
}

export function getRealtimeUrl(baseUrl = API_BASE_URL): string {
  const url = new URL(baseUrl, window.location.origin)
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
  url.pathname = `${url.pathname.replace(/\/$/, '')}/ws/v1/realtime`
  url.search = ''
  return url.toString()
}
