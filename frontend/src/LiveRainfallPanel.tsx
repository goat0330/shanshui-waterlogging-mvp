import { useEffect, useMemo, useState } from 'react'
import type { RainfallSnapshot, ShanghaiWaterRealtimeState, ShanghaiWaterSnapshot } from './types'

interface LiveRainfallPanelProps {
  rainfall: RainfallSnapshot
  stationName?: string
  realSource?: ShanghaiWaterSnapshot | null
  runtime?: ShanghaiWaterRealtimeState | null
}

function formatClock(value: string) {
  return new Intl.DateTimeFormat('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  }).format(new Date(value))
}

function formatDuration(minutes = 0) {
  const hours = Math.floor(minutes / 60)
  const remainder = minutes % 60
  return `${hours} h ${remainder.toString().padStart(2, '0')} min`
}

function Metric({ value, unit, label, tone, compact = false }: { value: string; unit?: string; label: string; tone: string; compact?: boolean }) {
  return (
    <div className={`metric-value metric-value--${tone} ${compact ? 'metric-value--compact' : ''}`}>
      <div><strong>{value}</strong>{unit && <small>{unit}</small>}</div>
      <span>{label}</span>
    </div>
  )
}

function freshnessLabel(runtime: ShanghaiWaterRealtimeState | null | undefined, observedAt: string | null) {
  if (!runtime) return '前端已连接实时源'
  if (runtime.status === 'degraded') return runtime.lastError ? '采集降级 · 保留最近有效数据' : '采集降级'
  if (!runtime.polledAt) return '后端采集器启动中'
  if (runtime.rainfallChangedThisPoll) return '已刷新 · 雨量源有新观测'
  if (!observedAt) return '已刷新 · 暂无源站观测'
  return '已刷新 · 源站暂无新观测'
}

export function LiveRainfallPanel({ rainfall, stationName = '徐家汇站', realSource = null, runtime = null }: LiveRainfallPanelProps) {
  const realStations = realSource?.rainfall ?? []
  const [selectedStationId, setSelectedStationId] = useState<string>('')

  useEffect(() => {
    if (realStations.length === 0) return
    if (!selectedStationId || !realStations.some((item) => item.stationId === selectedStationId)) {
      const strongest = realStations.slice().sort((a, b) => b.rainfallValue - a.rainfallValue)[0]
      setSelectedStationId(strongest.stationId)
    }
  }, [realSource?.fetchedAt, selectedStationId])

  const selectedStation = realStations.find((item) => item.stationId === selectedStationId) ?? null
  const realMode = Boolean(selectedStation)
  const backendHistory = selectedStation ? runtime?.rainfallHistory[selectedStation.stationId] ?? [] : []
  const trend = realMode
    ? (backendHistory.length > 0
        ? backendHistory.map((item) => item.rainfallValue)
        : [selectedStation!.rainfallValue])
    : rainfall.trend.map((item) => item.valueMmH)

  const chart = useMemo(() => {
    const width = 360
    const height = 112
    const safeValues = trend.length > 0 ? trend : [0]
    const max = Math.max(...safeValues, realMode ? 1 : 100)
    const points = safeValues.map((value, index) => ({
      x: (index / Math.max(safeValues.length - 1, 1)) * width,
      y: height - (value / max) * (height - 16) - 4,
      value,
    }))
    return {
      points,
      line: points.map((point) => `${point.x},${point.y}`).join(' '),
      area: `0,${height} ${points.map((point) => `${point.x},${point.y}`).join(' ')} ${width},${height}`,
    }
  }, [realMode, trend])

  const updatedAt = realMode
    ? runtime?.polledAt ?? realSource?.fetchedAt ?? selectedStation!.observedAt
    : rainfall.updatedAt
  const chartLabel = realMode ? '源值趋势' : '雨强趋势'
  const chartUnit = realMode ? 'RAINVALUE' : 'mm/h'
  const currentChartValue = realMode ? selectedStation!.rainfallValue : rainfall.intensityMmH
  const sourceObservedAt = selectedStation?.observedAt ?? runtime?.latestSourceObservedAt ?? null
  const runtimeHint = realMode ? freshnessLabel(runtime, sourceObservedAt) : null

  return (
    <section className="panel rainfall-panel" data-state="ready">
      <div className="panel-header">
        <h2><span className="panel-title-mark">⌁</span>{realMode ? '上海水务实时雨量' : '实时雨情'}</h2>
        <div className="rainfall-panel-tools">
          <span>更新于 {formatClock(updatedAt)}</span>
          {realMode ? (
            <select className="station-select" value={selectedStationId} aria-label="选择上海水务雨量站" onChange={(event) => setSelectedStationId(event.target.value)}>
              {realStations.map((station) => <option key={station.stationId} value={station.stationId}>{station.stationName}</option>)}
            </select>
          ) : <button type="button" className="station-select">{stationName}<span>⌄</span></button>}
        </div>
      </div>
      <div className="rainfall-metrics">
        {realMode ? (
          <>
            <Metric value={selectedStation!.rainfallValue.toFixed(1)} label="源站雨量值" tone="cyan" />
            <Metric value={String(realStations.length)} unit="站" label="当前可用站点" tone="blue" />
            <Metric value={formatClock(selectedStation!.observedAt).slice(0, 5)} label="最新观测" tone="white" compact />
          </>
        ) : (
          <>
            <Metric value={rainfall.intensityMmH.toFixed(1)} unit="mm/h" label="当前雨强" tone="cyan" />
            <Metric value={rainfall.cumulativeMm.toFixed(1)} unit="mm" label="累计雨量" tone="blue" />
            <Metric value={formatDuration(rainfall.durationMinutes)} label="持续时长" tone="white" compact />
          </>
        )}
      </div>
      <div className="chart-heading"><span>{chartLabel}</span><small>({chartUnit})</small></div>
      <div className="rainfall-chart" aria-label={realMode ? '后端保存的上海水务源值趋势' : '最近 120 分钟雨强趋势图'}>
        <svg viewBox="0 0 360 144" preserveAspectRatio="none" role="img">
          <defs>
            <linearGradient id="rainAreaLive" x1="0" x2="0" y1="0" y2="1">
              <stop offset="0" stopColor="#24d8ee" stopOpacity="0.35" />
              <stop offset="1" stopColor="#24d8ee" stopOpacity="0" />
            </linearGradient>
          </defs>
          {[0, 1, 2, 3].map((line) => <line key={line} x1="0" x2="360" y1={20 + line * 27} y2={20 + line * 27} className="chart-grid-line" />)}
          <polygon points={chart.area} fill="url(#rainAreaLive)" />
          <polyline points={chart.line} fill="none" className="rain-line" />
          {chart.points.map((point, index) => (
            <circle key={`${point.x}-${index}`} cx={point.x} cy={point.y} r={index === chart.points.length - 1 ? 4.6 : 2.4} className={index === chart.points.length - 1 ? 'rain-point rain-point--current' : 'rain-point'} />
          ))}
          <text x="4" y="140" className="chart-axis-label">{realMode ? '后端实时历史' : '−120min'}</text>
          <text x="314" y="140" className="chart-axis-label">NOW</text>
          <text x="334" y={(chart.points.at(-1)?.y ?? 32) - 8} className="chart-current-label">{currentChartValue.toFixed(1)}</text>
        </svg>
        {realMode && (
          <span className="rainfall-live-hint" title={runtime?.lastError ?? undefined}>
            {runtimeHint} · {backendHistory.length} 条源观测 · 后端 {Math.round(runtime?.pollIntervalSeconds ?? 60)}s 自动采集
          </span>
        )}
      </div>
    </section>
  )
}
