import { useMemo } from 'react'
import { getFloodPointEventId, getFloodPointSensorId } from '../data/mappings'
import type { AIAnalysis, Camera, FloodEvent, FloodForecast, FloodPoint } from '../types'

export interface SelectedEventCoordinatorInput {
  selectedPointId: string
  points: FloodPoint[]
  event: FloodEvent | null
  forecast: FloodForecast | null
  analysis: AIAnalysis | null
  camera: Camera | null
  eventsById?: Record<string, FloodEvent>
  forecastsByEventId?: Record<string, FloodForecast>
  analysesByEventId?: Record<string, AIAnalysis>
  camerasById?: Record<string, Camera>
}

export interface SelectedEventCoordinatorResult {
  selectedPoint: FloodPoint | null
  eventId: string | null
  event: FloodEvent | null
  forecast: FloodForecast | null
  analysis: AIAnalysis | null
  camera: Camera | null
  sensorId: string | null
}

export function coordinateSelectedEvent(input: SelectedEventCoordinatorInput): SelectedEventCoordinatorResult {
  const selectedPoint = input.points.find((point) => point.id === input.selectedPointId) ?? null
  const eventId = getFloodPointEventId(selectedPoint)
  const event = eventId
    ? input.event?.id === eventId
      ? input.event
      : input.eventsById?.[eventId] ?? null
    : null
  const forecast = event
    ? input.forecast?.eventId === event.id
      ? input.forecast
      : input.forecastsByEventId?.[event.id] ?? null
    : null
  const analysis = event
    ? input.analysis?.eventId === event.id
      ? input.analysis
      : input.analysesByEventId?.[event.id] ?? null
    : null
  const camera = event?.cameraId
    ? input.camera?.id === event.cameraId
      ? input.camera
      : input.camerasById?.[event.cameraId] ?? null
    : null

  return {
    selectedPoint,
    eventId,
    event,
    forecast,
    analysis,
    camera,
    sensorId: getFloodPointSensorId(selectedPoint),
  }
}

export function useSelectedEventCoordinator(input: SelectedEventCoordinatorInput): SelectedEventCoordinatorResult {
  return useMemo(
    () => coordinateSelectedEvent(input),
    [
      input.selectedPointId,
      input.points,
      input.event,
      input.forecast,
      input.analysis,
      input.camera,
      input.eventsById,
      input.forecastsByEventId,
      input.analysesByEventId,
      input.camerasById,
    ],
  )
}
