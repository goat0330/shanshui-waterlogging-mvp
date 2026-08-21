import type { FloodForecast, ForecastFrame, ForecastKey } from '../types'

export interface ForecastSurfaceAdapterResult {
  selectedForecastKey: ForecastKey
  frame: ForecastFrame | null
}

export function getForecastSurfaceAdapter(forecast: FloodForecast | null, selectedForecastKey: ForecastKey): ForecastSurfaceAdapterResult {
  return {
    selectedForecastKey,
    frame: forecast?.frames.find((frame) => frame.timeKey === selectedForecastKey) ?? null,
  }
}
