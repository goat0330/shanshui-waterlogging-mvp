import { useEffect, useState } from 'react'
import { API_BASE_URL, apiClient } from '../services/apiClient'
import type { ShanghaiWaterSnapshot } from '../types'

const EXTERNAL_REFRESH_INTERVAL_MS = 60_000

export type ExternalSourceStatus = 'disabled' | 'loading' | 'ready' | 'degraded'

interface UseExternalDataRefreshOptions {
  enabled: boolean
  initialShanghaiWater?: ShanghaiWaterSnapshot | null
}

export function useExternalDataRefresh({ enabled, initialShanghaiWater = null }: UseExternalDataRefreshOptions) {
  const [shanghaiWater, setShanghaiWater] = useState<ShanghaiWaterSnapshot | null>(initialShanghaiWater)
  const [waterStatus, setWaterStatus] = useState<ExternalSourceStatus>(enabled ? 'loading' : 'disabled')
  const [meteorologyStatus, setMeteorologyStatus] = useState<ExternalSourceStatus>(enabled ? 'loading' : 'disabled')
  const [lastRefreshAt, setLastRefreshAt] = useState<string | null>(null)

  useEffect(() => {
    if (initialShanghaiWater) setShanghaiWater(initialShanghaiWater)
  }, [initialShanghaiWater?.fetchedAt])

  useEffect(() => {
    if (!enabled) {
      setWaterStatus('disabled')
      setMeteorologyStatus('disabled')
      return
    }

    let disposed = false

    const refresh = async () => {
      const [waterResult, meteorologyResult] = await Promise.allSettled([
        apiClient.getShanghaiWater(),
        fetch(`${API_BASE_URL}/api/v1/context/meteorology`, { cache: 'no-store' }),
      ])
      if (disposed) return

      if (waterResult.status === 'fulfilled' && waterResult.value) {
        setShanghaiWater(waterResult.value)
        setWaterStatus('ready')
      } else {
        setWaterStatus('degraded')
      }

      if (meteorologyResult.status === 'fulfilled' && meteorologyResult.value.ok) {
        setMeteorologyStatus('ready')
      } else {
        setMeteorologyStatus('degraded')
      }
      setLastRefreshAt(new Date().toISOString())
    }

    void refresh()
    const timer = window.setInterval(() => void refresh(), EXTERNAL_REFRESH_INTERVAL_MS)
    return () => {
      disposed = true
      window.clearInterval(timer)
    }
  }, [enabled])

  return { shanghaiWater, waterStatus, meteorologyStatus, lastRefreshAt }
}
