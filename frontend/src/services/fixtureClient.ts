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
} from '../types'

const fixtureEvent = homeFixtures.event
const fixtureForecast = homeFixtures.forecast
const fixtureAnalysis = homeFixtures.analysis
const fixtureCamera = homeFixtures.camera

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
  getTimeline: async (scenarioId: string): Promise<ScenarioTimeline> => {
    if (homeFixtures.timeline.scenarioId !== scenarioId) throw notFound('timeline', scenarioId)
    return homeFixtures.timeline
  },
}
