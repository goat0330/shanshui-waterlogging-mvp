import { useCallback, useEffect, useState } from 'react'
import { DEFAULT_FLOOD_POINT_ID, DEFAULT_SCENARIO_ID, FORMAL_EVENT_BY_FLOOD_POINT, SENSOR_FLOOD_POINT_MAPPINGS } from '../data/mappings'
import { apiClient, DATA_SOURCE, type DataSource } from '../services/apiClient'
import { fixtureClient } from '../services/fixtureClient'
import type { DashboardData, SensorState } from '../types'

const client = DATA_SOURCE === 'api' ? apiClient : fixtureClient
const defaultEventId = FORMAL_EVENT_BY_FLOOD_POINT[DEFAULT_FLOOD_POINT_ID]

async function loadDashboardData(): Promise<DashboardData> {
  const [overview, rainfall, rainfallRanking, points, event, forecast, analysis, cameras, timeline] = await Promise.all([
    client.getOverview(),
    client.getRainfall(),
    client.getRainfallStationRanking(),
    client.listFloodPoints(),
    client.getFloodEvent(defaultEventId),
    client.getFloodForecast(defaultEventId),
    client.getFloodAnalysis(defaultEventId),
    client.listCameras(),
    client.getTimeline(DEFAULT_SCENARIO_ID),
  ])

  return {
    overview,
    rainfall,
    rainfallRanking,
    points,
    event,
    forecast,
    camera: event.cameraId ? cameras.find((camera) => camera.id === event.cameraId) ?? null : null,
    analysis,
    timeline,
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
    if (!mapping) return

    setData((current) => {
      if (!current) return current
      return {
        ...current,
        points: current.points.map((point) => point.id === mapping.floodPointId ? { ...point, depthCm: sensor.depthCm } : point),
        event: current.event?.id === mapping.eventId ? { ...current.event, currentDepthCm: sensor.depthCm } : current.event,
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
