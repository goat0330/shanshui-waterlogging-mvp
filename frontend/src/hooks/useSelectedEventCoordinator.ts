import { useMemo } from 'react'
import { FORMAL_EVENT_BY_FLOOD_POINT } from '../data/mappings'
import type { AIAnalysis, Camera, FloodEvent, FloodForecast, FloodPoint } from '../types'

export interface SelectedEventCoordinatorInput {
  selectedPointId: string
  points: FloodPoint[]
  event: FloodEvent | null
  forecast: FloodForecast | null
  analysis: AIAnalysis | null
  camera: Camera | null
}

export interface SelectedEventCoordinatorResult {
  selectedPoint: FloodPoint | null
  eventId: string | null
  event: FloodEvent | null
  forecast: FloodForecast | null
  analysis: AIAnalysis | null
  camera: Camera | null
}

export function coordinateSelectedEvent(input: SelectedEventCoordinatorInput): SelectedEventCoordinatorResult {
  const selectedPoint = input.points.find((point) => point.id === input.selectedPointId) ?? null
  const eventId = selectedPoint ? FORMAL_EVENT_BY_FLOOD_POINT[selectedPoint.id] ?? null : null
  const event = eventId && input.event?.id === eventId ? input.event : null

  return {
    selectedPoint,
    eventId,
    event,
    forecast: event && input.forecast?.eventId === event.id ? input.forecast : null,
    analysis: event && input.analysis?.eventId === event.id ? input.analysis : null,
    camera: event?.cameraId && input.camera?.id === event.cameraId ? input.camera : null,
  }
}

export function useSelectedEventCoordinator(input: SelectedEventCoordinatorInput): SelectedEventCoordinatorResult {
  return useMemo(
    () => coordinateSelectedEvent(input),
    [input.selectedPointId, input.points, input.event, input.forecast, input.analysis, input.camera],
  )
}
