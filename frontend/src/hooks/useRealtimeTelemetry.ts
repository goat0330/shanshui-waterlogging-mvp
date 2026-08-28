import { useEffect, useState } from 'react'
import { DATA_SOURCE, getRealtimeUrl } from '../services/apiClient'
import type { EventIntelligenceUpdate, MeteorologyRealtimeState, SensorState, ShanghaiWaterRealtimeState } from '../types'

export type RealtimeStatus = 'disabled' | 'connecting' | 'connected' | 'fallback'

const REST_REFRESH_INTERVAL_MS = 15_000
const WS_RECONNECT_DELAY_MS = 5_000

interface RealtimeEnvelope {
  type?: string
  timestamp?: string
  payload?: unknown
}

function isSensorState(value: unknown): value is SensorState {
  if (!value || typeof value !== 'object') return false
  const candidate = value as Partial<SensorState>
  return typeof candidate.sensorId === 'string'
    && typeof candidate.siteId === 'string'
    && typeof candidate.depthCm === 'number'
    && typeof candidate.depthMm === 'number'
    && typeof candidate.waterDetected === 'boolean'
    && typeof candidate.observedAt === 'string'
    && typeof candidate.receivedAt === 'string'
    && Boolean(candidate.coordinates)
}

function isShanghaiWaterRealtimeState(value: unknown): value is ShanghaiWaterRealtimeState {
  if (!value || typeof value !== 'object') return false
  const candidate = value as Partial<ShanghaiWaterRealtimeState>
  return typeof candidate.status === 'string'
    && typeof candidate.pollIntervalSeconds === 'number'
    && typeof candidate.rainfallHistory === 'object'
}

function isMeteorologyRealtimeState(value: unknown): value is MeteorologyRealtimeState {
  if (!value || typeof value !== 'object') return false
  const candidate = value as Partial<MeteorologyRealtimeState>
  return typeof candidate.status === 'string'
    && typeof candidate.pollIntervalSeconds === 'number'
    && typeof candidate.sourceChangedThisPoll === 'boolean'
}

function isEventIntelligenceUpdate(value: unknown): value is EventIntelligenceUpdate {
  if (!value || typeof value !== 'object') return false
  const candidate = value as Partial<EventIntelligenceUpdate>
  return Boolean(candidate.event)
    && Boolean(candidate.forecast)
    && Boolean(candidate.analysis)
    && typeof candidate.event?.id === 'string'
}

export interface UseRealtimeTelemetryOptions {
  enabled?: boolean
  onSensorUpdated: (sensor: SensorState) => void
  onShanghaiWaterUpdated?: (state: ShanghaiWaterRealtimeState) => void
  onMeteorologyUpdated?: (state: MeteorologyRealtimeState) => void
  onEventIntelligenceUpdated?: (update: EventIntelligenceUpdate) => void
  onScenarioStarted?: (payload: unknown) => void
  onRestFallback?: () => void
}

export interface UseRealtimeTelemetryResult {
  status: RealtimeStatus
  lastEventAt: string | null
}

export function useRealtimeTelemetry({ enabled = DATA_SOURCE === 'api', onSensorUpdated, onShanghaiWaterUpdated, onMeteorologyUpdated, onEventIntelligenceUpdated, onScenarioStarted, onRestFallback }: UseRealtimeTelemetryOptions): UseRealtimeTelemetryResult {
  const [status, setStatus] = useState<RealtimeStatus>(enabled ? 'connecting' : 'disabled')
  const [lastEventAt, setLastEventAt] = useState<string | null>(null)

  useEffect(() => {
    if (!enabled || DATA_SOURCE !== 'api') {
      setStatus('disabled')
      return
    }

    let disposed = false
    let socket: WebSocket | null = null
    let restRefreshTimer: number | null = null
    let reconnectTimer: number | null = null

    const refreshFromRest = () => {
      if (disposed) return
      onRestFallback?.()
    }

    const clearRestRefresh = () => {
      if (restRefreshTimer === null) return
      window.clearInterval(restRefreshTimer)
      restRefreshTimer = null
    }

    const startRestFallback = () => {
      if (disposed) return
      setStatus('fallback')
      if (restRefreshTimer !== null) return
      refreshFromRest()
      restRefreshTimer = window.setInterval(refreshFromRest, REST_REFRESH_INTERVAL_MS)
    }

    const scheduleReconnect = () => {
      if (disposed || reconnectTimer !== null) return
      reconnectTimer = window.setTimeout(() => {
        reconnectTimer = null
        connect()
      }, WS_RECONNECT_DELAY_MS)
    }

    const handleSocketClosed = (candidate: WebSocket) => {
      if (disposed || socket !== candidate) return
      socket = null
      startRestFallback()
      scheduleReconnect()
    }

    const connect = () => {
      if (disposed || socket !== null) return
      setStatus('connecting')

      try {
        socket = new WebSocket(getRealtimeUrl())
      } catch {
        startRestFallback()
        scheduleReconnect()
        return
      }

      const candidate = socket
      candidate.onopen = () => {
        if (disposed || socket !== candidate) return
        clearRestRefresh()
        setStatus('connected')
      }

      candidate.onmessage = (message) => {
        if (disposed || socket !== candidate) return
        let envelope: RealtimeEnvelope
        try {
          envelope = JSON.parse(message.data) as RealtimeEnvelope
        } catch {
          return
        }

        const eventTime = envelope.timestamp ?? new Date().toISOString()
        if (envelope.type === 'scenario.started') {
          setLastEventAt(eventTime)
          onScenarioStarted?.(envelope.payload)
          return
        }
        if (envelope.type === 'sensor.updated' && isSensorState(envelope.payload)) {
          setLastEventAt(eventTime)
          onSensorUpdated(envelope.payload)
          return
        }
        if (envelope.type === 'external.shanghai_water.updated' && isShanghaiWaterRealtimeState(envelope.payload)) {
          setLastEventAt(eventTime)
          onShanghaiWaterUpdated?.(envelope.payload)
          return
        }
        if (envelope.type === 'meteorology.updated' && isMeteorologyRealtimeState(envelope.payload)) {
          setLastEventAt(eventTime)
          onMeteorologyUpdated?.(envelope.payload)
          return
        }
        if (envelope.type === 'event.intelligence.updated' && isEventIntelligenceUpdate(envelope.payload)) {
          setLastEventAt(eventTime)
          onEventIntelligenceUpdated?.(envelope.payload)
        }
      }

      candidate.onerror = () => {
        if (disposed || socket !== candidate) return
        startRestFallback()
        try {
          candidate.close()
        } catch {
          // close event will schedule reconnect when available
        }
      }
      candidate.onclose = () => handleSocketClosed(candidate)
    }

    connect()

    return () => {
      disposed = true
      clearRestRefresh()
      if (reconnectTimer !== null) window.clearTimeout(reconnectTimer)
      if (socket !== null) {
        const activeSocket = socket
        socket = null
        activeSocket.onopen = null
        activeSocket.onmessage = null
        activeSocket.onerror = null
        activeSocket.onclose = null
        try {
          activeSocket.close()
        } catch {
          // socket already closed
        }
      }
    }
  }, [enabled, onEventIntelligenceUpdated, onMeteorologyUpdated, onRestFallback, onScenarioStarted, onSensorUpdated, onShanghaiWaterUpdated])

  return { status, lastEventAt }
}
