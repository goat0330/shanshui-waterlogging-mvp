import analysisFixture from '../../../contracts/fixtures/analysis-FP202506010024.json'
import camerasFixture from '../../../contracts/fixtures/cameras.json'
import dashboardOverviewFixture from '../../../contracts/fixtures/dashboard-overview.json'
import eventFixture from '../../../contracts/fixtures/event-FP202506010024.json'
import floodPointsFixture from '../../../contracts/fixtures/flood-points.json'
import forecastFixture from '../../../contracts/fixtures/forecast-FP202506010024.json'
import rainfallFixture from '../../../contracts/fixtures/rainfall-current.json'
import rainfallRankingFixture from '../../../contracts/fixtures/rainfall-stations-ranking.json'
import sensorFloodPointMappingFixture from '../../../contracts/fixtures/sensor-floodpoint-mapping.json'
import timelineFixture from '../../../contracts/fixtures/timeline-SHANGHAI-DEMO-001.json'
import type { HomeFixtures, SensorFloodPointMapping } from '../types'

export const sensorFloodPointMapping = sensorFloodPointMappingFixture as SensorFloodPointMapping

const demoCamera = camerasFixture[0] as HomeFixtures['camera']
const localDemoVideoUrl = import.meta.env.VITE_DEMO_VIDEO_URL?.trim()
const localDemoOverlayUrl = import.meta.env.VITE_DEMO_VIDEO_OVERLAY_URL?.trim()
const demoOverview = dashboardOverviewFixture as HomeFixtures['overview']

// Demo-only projection keeps the legacy fixture visible in the same shape as the backend summary.
// API mode remains authoritative and normalizes waterloggingSituation at the hook boundary.
const fixtureDerivedSummary: NonNullable<HomeFixtures['overview']['summary']> = {
  totalEvents: 1,
  changeVs1h: 108,
  status: { pending: 0, processing: 1, mitigated: 0 },
  topAreas: [{ name: '黄浦区', eventCount: 1 }],
  maxDepthCm: 28.6,
  averageDepthCm: 19.4,
  averageResponseMinutes: 32.4,
  newToday: 1,
}

export const homeFixtures: HomeFixtures = {
  overview: { ...demoOverview, summary: fixtureDerivedSummary },
  rainfall: rainfallFixture as HomeFixtures['rainfall'],
  rainfallRanking: rainfallRankingFixture as HomeFixtures['rainfallRanking'],
  points: floodPointsFixture as HomeFixtures['points'],
  event: eventFixture as HomeFixtures['event'],
  forecast: forecastFixture as HomeFixtures['forecast'],
  camera: {
    ...demoCamera,
    ...(localDemoVideoUrl ? { mediaUrl: localDemoVideoUrl } : {}),
    ...(localDemoOverlayUrl ? { overlayUrl: localDemoOverlayUrl } : {}),
  },
  analysis: analysisFixture as HomeFixtures['analysis'],
  timeline: timelineFixture as HomeFixtures['timeline'],
}
