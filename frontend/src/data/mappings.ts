import { sensorFloodPointMapping } from './homeFixtures'
import type { FloodPoint } from '../types'

export const FORMAL_EVENT_BY_FLOOD_POINT: Record<string, string> = {
  [sensorFloodPointMapping.floodPointId]: sensorFloodPointMapping.eventId,
}

export const SENSOR_FLOOD_POINT_MAPPINGS = [sensorFloodPointMapping]

export const DEFAULT_FLOOD_POINT_ID = sensorFloodPointMapping.floodPointId
export const DEFAULT_SCENARIO_ID = 'SHANGHAI-DEMO-001'

function hasRelationField(point: FloodPoint, field: 'eventId' | 'sensorId'): boolean {
  return Object.prototype.hasOwnProperty.call(point, field)
}

export function getFloodPointEventId(point: FloodPoint | null): string | null {
  if (!point) return null
  if (hasRelationField(point, 'eventId')) return point.eventId ?? null
  return FORMAL_EVENT_BY_FLOOD_POINT[point.id] ?? null
}

export function getFloodPointSensorId(point: FloodPoint | null): string | null {
  if (!point) return null
  if (hasRelationField(point, 'sensorId')) return point.sensorId ?? null
  return SENSOR_FLOOD_POINT_MAPPINGS.find((item) => item.floodPointId === point.id)?.sensorId ?? null
}
