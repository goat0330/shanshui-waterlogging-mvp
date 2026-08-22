import { homeFixtures } from '../data/homeFixtures'
import type {
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

const fixtureEvent = homeFixtures.event
const fixtureForecast = homeFixtures.forecast
const fixtureAnalysis = homeFixtures.analysis
const fixtureCamera = homeFixtures.camera
const fixtureSensor: SensorState = {
  sensorId: 'SSZJ-NODE-001',
  siteId: 'SITE-RML-BJDD',
  coordinates: fixtureEvent.coordinates,
  depthMm: fixtureEvent.currentDepthCm * 10,
  depthCm: fixtureEvent.currentDepthCm,
  waterDetected: fixtureEvent.currentDepthCm > 0,
  observedAt: fixtureEvent.startedAt,
  receivedAt: homeFixtures.overview.updatedAt,
  transport: 'SIMULATOR',
  source: 'DEMO_DEVICE',
}

function notFound(resource: string, id: string): Error {
  return new Error(`Fixture ${resource} not found: ${id}`)
}

export const fixtureClient: DashboardDataClient = {
  getOverview: async (): Promise<DashboardOverview> => homeFixtures.overview,
  getRainfall: async (): Promise<RainfallSnapshot> => homeFixtures.rainfall,
  getRainfallStationRanking: async (): Promise<RainfallStationRankingItem[]> => homeFixtures.rainfallRanking,
  listFloodPoints: async (): Promise<FloodPoint[]> => homeFixtures.points,
  getFloodEvent: async (eventId: string): Promise<FloodEvent> => {
    if (fixtureEvent.id !== eventId) throw notFound('event', eventId)
    return fixtureEvent
  },
  getFloodForecast: async (eventId: string): Promise<FloodForecast> => {
    if (fixtureForecast.eventId !== eventId) throw notFound('forecast', eventId)
    return fixtureForecast
  },
  getFloodAnalysis: async (eventId: string) => {
    if (fixtureAnalysis.eventId !== eventId) throw notFound('analysis', eventId)
    return fixtureAnalysis
  },
  listCameras: async () => [fixtureCamera],
  getCamera: async (cameraId: string) => {
    if (fixtureCamera.id !== cameraId) throw notFound('camera', cameraId)
    return fixtureCamera
  },
  getSensorState: async (sensorId: string): Promise<SensorState> => {
    if (fixtureSensor.sensorId !== sensorId) throw notFound('sensor', sensorId)
    return fixtureSensor
  },
  getTimeline: async (scenarioId: string): Promise<ScenarioTimeline> => {
    if (homeFixtures.timeline.scenarioId !== scenarioId) throw notFound('timeline', scenarioId)
    return homeFixtures.timeline
  },
}
