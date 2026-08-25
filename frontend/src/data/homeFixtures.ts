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
// API mode remains authoritative and reads waterloggingSituation directly.
const fixtureDerivedSituation: NonNullable<HomeFixtures['overview']['waterloggingSituation']> = {
  totalEvents: 1,
  changeVsHour: 108,
  disposition: { pending: 0, handling: 1, relieved: 0 },
  topDistricts: [{ district: '黄浦区', eventCount: 1 }],
  metrics: { maxDepthCm: 28.6, avgDepthCm: 19.4, avgResponseMinutes: 32.4, newToday: 1 },
  source: 'FIXTURE_DERIVED',
}

export const homeFixtures: HomeFixtures = {
  overview: { ...demoOverview, waterloggingSituation: fixtureDerivedSituation },
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
