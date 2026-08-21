import { sensorFloodPointMapping } from './homeFixtures'

export const FORMAL_EVENT_BY_FLOOD_POINT: Record<string, string> = {
  [sensorFloodPointMapping.floodPointId]: sensorFloodPointMapping.eventId,
}

export const SENSOR_FLOOD_POINT_MAPPINGS = [sensorFloodPointMapping]

export const DEFAULT_FLOOD_POINT_ID = sensorFloodPointMapping.floodPointId
export const DEFAULT_SCENARIO_ID = 'SHANGHAI-DEMO-001'
