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
import type { DashboardData, HistoricalFloodCase, SensorState, FloodPoint } from '../types'

const defaultEventId = FORMAL_EVENT_BY_FLOOD_POINT[DEFAULT_FLOOD_POINT_ID]
const defaultSensorId = SENSOR_FLOOD_POINT_MAPPINGS[0]?.sensorId ?? 'SSZJ-NODE-001'
const localDemoVideoUrl = import.meta.env.VITE_DEMO_VIDEO_URL?.trim()
const localDemoOverlayUrl = import.meta.env.VITE_DEMO_VIDEO_OVERLAY_URL?.trim()

interface LoadedDomain<T> {
  value: T
  fromFixture: boolean
  apiSucceeded: boolean
}

interface DashboardLoadResult {
  data: DashboardData
  degraded: boolean
  backendAvailable: boolean
}

async function loadDomain<T>(apiLoad: () => Promise<T>, fixtureLoad: () => Promise<T>): Promise<LoadedDomain<T>> {
  if (DATA_SOURCE !== 'api') return { value: await fixtureLoad(), fromFixture: false, apiSucceeded: false }
  try {
    return { value: await apiLoad(), fromFixture: false, apiSucceeded: true }
  } catch {
    return { value: await fixtureLoad(), fromFixture: true, apiSucceeded: false }
  }
}

function applyLocalDemoMedia(camera: DashboardData['camera']): DashboardData['camera'] {
  if (!camera || (!localDemoVideoUrl && !localDemoOverlayUrl)) return camera
  return {
    ...camera,
    ...(localDemoVideoUrl ? { mediaUrl: localDemoVideoUrl } : {}),
    ...(localDemoOverlayUrl ? { overlayUrl: localDemoOverlayUrl } : {}),
  }
}

function mergeHistoricalCasePoints(points: FloodPoint[], cases: HistoricalFloodCase[]): FloodPoint[] {
  const existingIds = new Set(points.map((point) => point.id))
  const historicalPoints = cases.flatMap((item) => {
    if (!item.coordinates) return []
    const id = `HIST-${item.candidateId}`
    if (existingIds.has(id)) return []
    return [{
      id,
      name: item.locationText,
      district: item.district,
      coordinates: item.coordinates,
      // Historical reports without a measured depth remain null semantically;
      // zero is only an internal map-shape placeholder and is never shown as evidence.
      depthCm: item.depthCm ?? 0,
      riskLevel: 'WARNING' as const,
      trend: 'STABLE' as const,
      eventId: null,
      sensorId: null,
      historicalCaseId: item.candidateId,
    } satisfies FloodPoint]
  })
  return [...points, ...historicalPoints]
}

async function loadDashboardData(): Promise<DashboardLoadResult> {
  const [overviewResult, rainfallResult, rankingResult, pointsResult, historyResult, camerasResult, timelineResult] = await Promise.all([
    loadDomain(apiClient.getOverview, fixtureClient.getOverview),
    loadDomain(apiClient.getRainfall, fixtureClient.getRainfall),
    loadDomain(apiClient.getRainfallStationRanking, fixtureClient.getRainfallStationRanking),
    loadDomain(apiClient.listFloodPoints, fixtureClient.listFloodPoints),
    loadDomain(apiClient.listHistoricalCases, fixtureClient.listHistoricalCases),
    loadDomain(apiClient.listCameras, fixtureClient.listCameras),
    loadDomain(() => apiClient.getTimeline(DEFAULT_SCENARIO_ID), () => fixtureClient.getTimeline(DEFAULT_SCENARIO_ID)),
  ])

  const coreResults = [overviewResult, rainfallResult, rankingResult, pointsResult, historyResult, camerasResult, timelineResult]
  const degraded = DATA_SOURCE === 'api' && coreResults.some((item) => item.fromFixture)
  const backendAvailable = DATA_SOURCE !== 'api' || coreResults.some((item) => item.apiSucceeded)
  const shanghaiWater = DATA_SOURCE === 'api' ? await apiClient.getShanghaiWater() : null

  const overview = overviewResult.value
  const rainfall = rainfallResult.value
  const rainfallRanking = rankingResult.value
  const pointsWithHistory = mergeHistoricalCasePoints(pointsResult.value, historyResult.value)
  const historicalCases = historyResult.value
  const cameras = camerasResult.value
  const timeline = timelineResult.value

  const eventIds = Array.from(new Set(pointsWithHistory.map(getFloodPointEventId).filter((value): value is string => Boolean(value))))
  let eventFallbackUsed = false
  const eventResults = await Promise.all(eventIds.map(async (eventId) => {
    try {
      const event = DATA_SOURCE === 'api' ? await apiClient.getFloodEvent(eventId) : await fixtureClient.getFloodEvent(eventId)
      const [forecast, analysis] = await Promise.all([
        (DATA_SOURCE === 'api' ? apiClient.getFloodForecast(eventId) : fixtureClient.getFloodForecast(eventId)).catch(() => null),
        (DATA_SOURCE === 'api' ? apiClient.getFloodAnalysis(eventId) : fixtureClient.getFloodAnalysis(eventId)).catch(() => null),
      ])
      return { event, forecast, analysis }
    } catch {
      if (DATA_SOURCE !== 'api') return null
      try {
        const event = await fixtureClient.getFloodEvent(eventId)
        const [forecast, analysis] = await Promise.all([
          fixtureClient.getFloodForecast(eventId).catch(() => null),
          fixtureClient.getFloodAnalysis(eventId).catch(() => null),
        ])
        eventFallbackUsed = true
        return { event, forecast, analysis }
      } catch {
        return null
      }
    }
  }))

  const validEventResults = eventResults.filter((result): result is NonNullable<typeof result> => result !== null)
  const eventsById = Object.fromEntries(validEventResults.map((result) => [result.event.id, result.event]))
  const forecastsByEventId = Object.fromEntries(validEventResults.flatMap((result) => result.forecast ? [[result.event.id, result.forecast]] : []))
  const analysesByEventId = Object.fromEntries(validEventResults.flatMap((result) => result.analysis ? [[result.event.id, result.analysis]] : []))
  const camerasById = Object.fromEntries(cameras.map((camera) => [camera.id, applyLocalDemoMedia(camera) ?? camera]))

  const sensorIds = Array.from(new Set(pointsWithHistory.map(getFloodPointSensorId).filter((value): value is string => Boolean(value))))
  const sensorResults = await Promise.all(sensorIds.map(async (sensorId) => {
    try {
      // API mode deliberately does not fabricate a sensor fallback. A missing
      // current state remains null until telemetry arrives.
      return DATA_SOURCE === 'api' ? await apiClient.getSensorState(sensorId) : await fixtureClient.getSensorState(sensorId)
    } catch {
      return null
    }
  }))
  const sensorsById = Object.fromEntries(sensorResults.filter((sensor): sensor is SensorState => sensor !== null).map((sensor) => [sensor.sensorId, sensor]))

  const defaultPoint = pointsWithHistory.find((point) => point.id === DEFAULT_FLOOD_POINT_ID) ?? null
  const requestedDefaultEventId = defaultPoint ? getFloodPointEventId(defaultPoint) : defaultEventId
  const event = requestedDefaultEventId ? eventsById[requestedDefaultEventId] ?? null : null
  const forecast = event ? forecastsByEventId[event.id] ?? null : null
  const analysis = event ? analysesByEventId[event.id] ?? null : null
  const camera = event?.cameraId ? camerasById[event.cameraId] ?? null : null

  return {
    degraded: degraded || eventFallbackUsed,
    backendAvailable,
    data: {
      overview,
      rainfall,
      rainfallRanking,
      points: pointsWithHistory,
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
    },
  }
}

export interface UseDashboardDataResult {
  data: DashboardData | null
  source: DataSource
  isLoading: boolean
  error: Error | null
  degraded: boolean
  reload: () => void
  applySensorState: (sensor: SensorState) => void
}

export function useDashboardData(): UseDashboardDataResult {
  const [data, setData] = useState<DashboardData | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)
  const [degraded, setDegraded] = useState(false)
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
      if (eventId && nextEventsById[eventId]) nextEventsById[eventId] = { ...nextEventsById[eventId], currentDepthCm: sensor.depthCm }
      const nextPoints = floodPointId
        ? current.points.map((point) => point.id === floodPointId ? { ...point, depthCm: sensor.depthCm } : point)
        : current.points
      const realtimeDepths = nextPoints.filter((point) => !point.historicalCaseId).map((point) => point.depthCm)
      const situation = current.overview.waterloggingSituation
      const nextOverview = situation
        ? {
            ...current.overview,
            updatedAt: sensor.receivedAt,
            waterloggingSituation: {
              ...situation,
              metrics: {
                ...situation.metrics,
                maxDepthCm: Math.max(...realtimeDepths, 0),
                avgDepthCm: realtimeDepths.length > 0 ? Number((realtimeDepths.reduce((sum, value) => sum + value, 0) / realtimeDepths.length).toFixed(1)) : 0,
              },
            },
          }
        : current.overview
      return {
        ...current,
        overview: nextOverview,
        sensor,
        sensorsById: { ...(current.sensorsById ?? {}), [sensor.sensorId]: sensor },
        points: nextPoints,
        event: current.event?.id === eventId ? { ...current.event, currentDepthCm: sensor.depthCm } : current.event,
        eventsById: nextEventsById,
      }
    })
  }, [])

  useEffect(() => {
    let cancelled = false
    setIsLoading(true)

    loadDashboardData()
      .then((result) => {
        if (cancelled) return
        setData(result.data)
        setDegraded(result.degraded)
        setError(DATA_SOURCE === 'api' && !result.backendAvailable ? new Error('Backend API unavailable') : null)
      })
      .catch((reason: unknown) => {
        if (cancelled) return
        setError(reason instanceof Error ? reason : new Error(String(reason)))
        setDegraded(true)
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false)
      })

    return () => { cancelled = true }
  }, [reloadToken])

  return { data, source: DATA_SOURCE, isLoading, error, degraded, reload, applySensorState }
}

export { DEFAULT_FLOOD_POINT_ID }
