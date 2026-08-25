import { useCallback, useEffect, useState } from 'react'
import {
  DEFAULT_FLOOD_POINT_ID,
  DEFAULT_SCENARIO_ID,
  FORMAL_EVENT_BY_FLOOD_POINT,
  getFloodPointEventId,
  getFloodPointSensorId,
  SENSOR_FLOOD_POINT_MAPPINGS,
} from '../data/mappings'
import { apiClient, DATA_SOURCE, type DataSource } from '../services/apiClient'
import { fixtureClient } from '../services/fixtureClient'
import type { DashboardData, DashboardOverview, SensorState } from '../types'

const client = DATA_SOURCE === 'api' ? apiClient : fixtureClient
const defaultEventId = FORMAL_EVENT_BY_FLOOD_POINT[DEFAULT_FLOOD_POINT_ID]
const defaultSensorId = SENSOR_FLOOD_POINT_MAPPINGS[0]?.sensorId ?? 'SSZJ-NODE-001'
const localDemoVideoUrl = import.meta.env.VITE_DEMO_VIDEO_URL?.trim()
const localDemoOverlayUrl = import.meta.env.VITE_DEMO_VIDEO_OVERLAY_URL?.trim()

function applyLocalDemoMedia(camera: DashboardData['camera']): DashboardData['camera'] {
  if (!camera || (!localDemoVideoUrl && !localDemoOverlayUrl)) return camera
  return {
    ...camera,
    ...(localDemoVideoUrl ? { mediaUrl: localDemoVideoUrl } : {}),
    ...(localDemoOverlayUrl ? { overlayUrl: localDemoOverlayUrl } : {}),
  }
}

async function loadDashboardData(): Promise<DashboardData> {
  const [overview, rainfall, rainfallRanking, points, historicalCases, cameras, timeline, shanghaiWater] = await Promise.all([
    client.getOverview(),
    client.getRainfall(),
    client.getRainfallStationRanking(),
    client.listFloodPoints(),
    client.listHistoricalCases().catch(() => []),
    client.listCameras(),
    client.getTimeline(DEFAULT_SCENARIO_ID),
    client.getShanghaiWater(),
  ])

  const eventIds = Array.from(new Set(points.map(getFloodPointEventId).filter((value): value is string => Boolean(value))))
  const eventResults = await Promise.all(eventIds.map(async (eventId) => {
    try {
      const event = await client.getFloodEvent(eventId)
      const [forecast, analysis] = await Promise.all([
        client.getFloodForecast(eventId).catch(() => null),
        client.getFloodAnalysis(eventId).catch(() => null),
      ])
      return { event, forecast, analysis }
    } catch {
      return null
    }
  }))

  const validEventResults = eventResults.filter((result): result is NonNullable<typeof result> => result !== null)
  const eventsById = Object.fromEntries(validEventResults.map((result) => [result.event.id, result.event]))
  const forecastsByEventId = Object.fromEntries(validEventResults.flatMap((result) => result.forecast ? [[result.event.id, result.forecast]] : []))
  const analysesByEventId = Object.fromEntries(validEventResults.flatMap((result) => result.analysis ? [[result.event.id, result.analysis]] : []))
  const camerasById = Object.fromEntries(cameras.map((camera) => [camera.id, applyLocalDemoMedia(camera) ?? camera]))

  const sensorIds = Array.from(new Set(points.map(getFloodPointSensorId).filter((value): value is string => Boolean(value))))
  const sensorResults = await Promise.all(sensorIds.map(async (sensorId) => {
    try {
      return await client.getSensorState(sensorId)
    } catch {
      return null
    }
  }))
  const sensorsById = Object.fromEntries(sensorResults.filter((sensor): sensor is SensorState => sensor !== null).map((sensor) => [sensor.sensorId, sensor]))

  const defaultPoint = points.find((point) => point.id === DEFAULT_FLOOD_POINT_ID) ?? null
  const requestedDefaultEventId = defaultPoint ? getFloodPointEventId(defaultPoint) : defaultEventId
  const event = requestedDefaultEventId ? eventsById[requestedDefaultEventId] ?? null : null
  const forecast = event ? forecastsByEventId[event.id] ?? null : null
  const analysis = event ? analysesByEventId[event.id] ?? null : null
  const camera = event?.cameraId ? camerasById[event.cameraId] ?? null : null

  return {
    overview,
    rainfall,
    rainfallRanking,
    points,
    historicalCases,
    event,
    forecast,
    camera,
    analysis,
    timeline,
    shanghaiWater,
    sensor: sensorsById[defaultSensorId] ?? null,
    eventsById,
    forecastsByEventId,
    analysesByEventId,
    camerasById,
    sensorsById,
  }
}

export interface UseDashboardDataResult {
  data: DashboardData | null
  source: DataSource
  isLoading: boolean
  error: Error | null
  reload: () => void
  applySensorState: (sensor: SensorState) => void
}

export function useDashboardData(): UseDashboardDataResult {
  const [data, setData] = useState<DashboardData | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)
  const [reloadToken, setReloadToken] = useState(0)

  const reload = useCallback(() => setReloadToken((value) => value + 1), [])

  const applySensorState = useCallback((sensor: SensorState) => {
    const mapping = SENSOR_FLOOD_POINT_MAPPINGS.find((item) => item.sensorId === sensor.sensorId)

    setData((current) => {
      if (!current) return current
      const selectedPoint = current.points.find((point) => getFloodPointSensorId(point) === sensor.sensorId) ?? null
      const floodPointId = selectedPoint?.id ?? mapping?.floodPointId
      const eventId = selectedPoint ? getFloodPointEventId(selectedPoint) : mapping?.eventId ?? null
      const nextEventsById = { ...(current.eventsById ?? {}) }
      if (eventId && nextEventsById[eventId]) {
        nextEventsById[eventId] = { ...nextEventsById[eventId], currentDepthCm: sensor.depthCm }
      }
      return {
        ...current,
        sensor,
        sensorsById: { ...(current.sensorsById ?? {}), [sensor.sensorId]: sensor },
        points: floodPointId ? current.points.map((point) => point.id === floodPointId ? { ...point, depthCm: sensor.depthCm } : point) : current.points,
        event: current.event?.id === eventId ? { ...current.event, currentDepthCm: sensor.depthCm } : current.event,
        eventsById: nextEventsById,
      }
    })
  }, [])

  useEffect(() => {
    let cancelled = false
    setIsLoading(true)

    loadDashboardData()
      .then((nextData) => {
        if (cancelled) return
        setData(nextData)
        setError(null)
      })
      .catch((reason: unknown) => {
        if (cancelled) return
        setError(reason instanceof Error ? reason : new Error(String(reason)))
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [reloadToken])

  return { data, source: DATA_SOURCE, isLoading, error, reload, applySensorState }
}

export { DEFAULT_FLOOD_POINT_ID }
