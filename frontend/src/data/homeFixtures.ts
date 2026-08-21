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

export const homeFixtures: HomeFixtures = {
  overview: dashboardOverviewFixture as HomeFixtures['overview'],
  rainfall: rainfallFixture as HomeFixtures['rainfall'],
  rainfallRanking: rainfallRankingFixture as HomeFixtures['rainfallRanking'],
  points: floodPointsFixture as HomeFixtures['points'],
  event: eventFixture as HomeFixtures['event'],
  forecast: forecastFixture as HomeFixtures['forecast'],
  camera: camerasFixture[0] as HomeFixtures['camera'],
  analysis: analysisFixture as HomeFixtures['analysis'],
  timeline: timelineFixture as HomeFixtures['timeline'],
}
