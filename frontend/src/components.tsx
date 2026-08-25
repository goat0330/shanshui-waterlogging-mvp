import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import type {
  AIAnalysis,
  Camera,
  DashboardOverview,
  DecisionProjection,
  FloodEvent,
  FloodForecast,
  FloodPoint,
  ForecastFrame,
  ForecastKey,
  PanelState,
  RainfallSnapshot,
  RainfallStationRankingItem,
  ScenarioTimeline,
  SensorState,
  VisionDepthObservation,
} from './types'
import type { VideoEvidenceState, VideoOverlayData } from './adapters/videoEvidenceAdapter'
import { CesiumScene } from './CesiumScene'
import { API_BASE_URL } from './services/apiClient'

const NAV_ITEMS = ['实时监测', '风险预警', '内涝分析', '预测预报', '资源调度', '系统管理']

const RISK_LABEL: Record<FloodPoint['riskLevel'], string> = {
  NORMAL: '正常',
  WARNING: '警戒',
  HIGH: '高风险',
  CRITICAL: '严重',
}

const FORECAST_LABEL: Record<ForecastKey, string> = {
  NOW: 'NOW',
  PLUS_10: '+10 min',
  PLUS_30: '+30 min',
}

const PANEL_STATE_LABEL: Record<Exclude<PanelState, 'ready'>, string> = {
  loading: '正在读取演示数据',
  empty: '暂无可展示数据',
  error: '数据暂不可用',
}

export interface AppShellProps {
  children: ReactNode
  className?: string
}

export function AppShell({ children, className = '' }: AppShellProps) {
  return <main className={`app-shell ${className}`.trim()}>{children}</main>
}

export interface TopNavProps {
  activeItem?: string
  overview?: DashboardOverview
  updatedAt?: string
}

export function TopNav({ activeItem = '实时监测', overview, updatedAt }: TopNavProps) {
  const time = updatedAt ?? overview?.updatedAt

  return (
    <header className="top-nav">
      <a className="brand" href="/" aria-label="返回实时监测首页">
        <LogoMark />
        <span className="brand-copy">
          <span className="brand-title">山水智鉴</span>
          <span className="brand-divider">|</span>
          <span className="brand-subtitle">城市内涝智能防控中心</span>
        </span>
      </a>

      {overview && (
        <div className="weather-strip" aria-label="城市天气">
          <span className="weather-location"><span className="pin-glyph">⌖</span>{overview.city}</span>
          <span className="weather-temp"><span className="weather-glyph">☼</span>{overview.weather.temperatureC}°C</span>
          <span className="weather-condition"><span className="rain-glyph">⌁</span>{overview.weather.condition}</span>
        </div>
      )}

      <nav className="top-nav-links" aria-label="主导航">
        {NAV_ITEMS.map((item) => (
          <a
            className={`top-nav-link ${activeItem === item ? 'is-active' : ''}`}
            href={item === '实时监测' ? '/' : '#mvp-shell'}
            key={item}
          >
            {item}
          </a>
        ))}
      </nav>

      <div className="top-nav-actions">
        <button className="icon-button notification-button" type="button" aria-label="查看通知">
          <span className="notification-bell">♧</span>
          <span className="notification-count">12</span>
        </button>
        <button className="icon-button fullscreen-button" type="button" aria-label="进入全屏">⛶</button>
        <button className="account-button" type="button" aria-label="管理员菜单">
          <span className="account-avatar">管</span>
          <span>管理员</span>
          <span className="account-chevron">⌄</span>
        </button>
        {time && <time dateTime={time}>{formatClock(time)}</time>}
      </div>
    </header>
  )
}

function LogoMark() {
  return (
    <svg className="logo-mark" viewBox="0 0 56 56" aria-hidden="true">
      <path d="M28 5 18 20l-7 9 17-7 17 7-7-9L28 5Z" fill="none" stroke="currentColor" strokeWidth="3" strokeLinejoin="round" />
      <path d="M5 36c8-5 15-5 23 0 8-5 15-5 23 0M8 45c7-4 13-4 20 0 7-4 13-4 20 0" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
      <circle cx="28" cy="28" r="3" fill="currentColor" />
    </svg>
  )
}

function formatClock(value: string) {
  return new Intl.DateTimeFormat('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  }).format(new Date(value))
}

function formatSceneEventName(value: string) {
  return value.replace(/\s*[×xX]\s*/g, ' · ')
}

function formatDate(value: string) {
  const date = new Date(value)
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
}

function formatDuration(minutes = 0) {
  const hours = Math.floor(minutes / 60)
  const remainder = minutes % 60
  return `${hours} h ${remainder.toString().padStart(2, '0')} min`
}

function formatRangeCm(range: [number | null, number | null]) {
  if (range[0] === null && range[1] === null) return 'null'
  return `${range[0] ?? '—'}–${range[1] ?? '—'} cm`
}

interface PanelProps {
  children: ReactNode
  className?: string
  state?: PanelState
}

function Panel({ children, className = '', state = 'ready' }: PanelProps) {
  return (
    <section className={`panel ${className}`.trim()} data-state={state}>
      {children}
      {state !== 'ready' && (
        <div className={`panel-state panel-state--${state}`} role="status">
          <span className="state-orb" />
          <span>{PANEL_STATE_LABEL[state]}</span>
        </div>
      )}
    </section>
  )
}

interface PanelHeaderProps {
  title: string
  meta?: ReactNode
  icon?: string
  className?: string
}

function PanelHeader({ title, meta, icon = '▰', className = '' }: PanelHeaderProps) {
  return (
    <div className={`panel-header ${className}`.trim()}>
      <h2><span className="panel-title-mark">{icon}</span>{title}</h2>
      {meta && <div className="panel-meta">{meta}</div>}
    </div>
  )
}

export interface StatusPanelProps {
  overview: DashboardOverview
  state?: PanelState
  variant?: 'default' | 'high-risk'
}

export function StatusPanel({ overview, state = 'ready', variant = 'default' }: StatusPanelProps) {
  const summary = overview.summary ?? null

  return (
    <Panel className={`status-panel ${variant === 'high-risk' ? 'status-panel--high-risk' : ''}`} state={state}>
      <PanelHeader title="当前积水态势" icon="◈" meta={<span>更新于 {formatClock(overview.updatedAt)}</span>} />
      {summary ? <StatusSummary summary={summary} /> : (
        <div className="status-summary-empty">
          <span className="status-summary-kicker">SUMMARY BLOCK</span>
          <strong>—</strong>
          <span>等待城市积水汇总</span>
          <small>当前模式未提供城市积水汇总</small>
        </div>
      )}
    </Panel>
  )
}

function StatusSummary({ summary }: { summary: NonNullable<DashboardOverview['summary']> }) {
  const deltaMagnitude = Math.abs(summary.changeVs1h).toFixed(1)
  const deltaPrefix = summary.changeVs1h > 0 ? '+' : summary.changeVs1h < 0 ? '−' : ''
  const deltaArrow = summary.changeVs1h > 0 ? '↑' : summary.changeVs1h < 0 ? '↓' : '→'
  const deltaTone = summary.changeVs1h > 0 ? 'up' : summary.changeVs1h < 0 ? 'down' : 'flat'
  const maxAreaEvents = Math.max(...summary.topAreas.map((area) => area.eventCount), 1)

  return (
    <div className="status-summary">
      <div className="status-summary-main">
        <div className="status-summary-ring" role="img" aria-label={`积水事件 ${summary.totalEvents} 起，较1小时前${deltaPrefix}${deltaMagnitude}`}>
          <div className="status-summary-ring-core">
            <strong>{summary.totalEvents}</strong>
            <span>积水事件</span>
            <span className={`status-summary-delta status-summary-delta--${deltaTone}`}>
              <b>{deltaArrow}</b>{deltaPrefix}{deltaMagnitude}<small>较1h前</small>
            </span>
          </div>
        </div>
        <div className="status-workflow" aria-label="事件处置状态">
          <StatusSummaryItem label="待处置" detail="新发现事件" value={summary.status.pending} tone="pending" />
          <StatusSummaryItem label="处理中" detail="正在排水 / 管控" value={summary.status.processing} tone="processing" />
          <StatusSummaryItem label="已缓解" detail="水位持续下降" value={summary.status.mitigated} tone="mitigated" />
        </div>
      </div>
      <div className="status-summary-lower">
        <div className="status-top-areas">
          <div className="status-section-label"><span>高发区域</span><small>TOP 3</small></div>
          {summary.topAreas.slice(0, 3).map((area, index) => (
            <div className="status-area-row" key={`${area.name}-${index}`}>
              <span className="status-area-rank">{String(index + 1).padStart(2, '0')}</span>
              <strong>{area.name}</strong>
              <span className="status-area-bar"><i style={{ width: `${(area.eventCount / maxAreaEvents) * 100}%` }} /></span>
              <small>{String(area.eventCount).padStart(2, '0')}</small>
            </div>
          ))}
          {summary.topAreas.length === 0 && <div className="status-subtle-empty">暂无高发区域</div>}
        </div>
        <div className="status-summary-metrics">
          <StatusSummaryMetric icon="depth" label="最大水深" value={`${summary.maxDepthCm.toFixed(1)} cm`} />
          <StatusSummaryMetric icon="average" label="平均水深" value={`${summary.averageDepthCm.toFixed(1)} cm`} />
          <StatusSummaryMetric icon="response" label="平均响应时间" value={`${summary.averageResponseMinutes.toFixed(0)} min`} />
          <StatusSummaryMetric icon="today" label="今日新增" value={`${summary.newToday > 0 ? '+' : ''}${summary.newToday} 起`} />
        </div>
      </div>
    </div>
  )
}

function StatusSummaryItem({ label, detail, value, tone }: { label: string; detail: string; value: number; tone: string }) {
  return (
    <div className={`status-workflow-item status-workflow-item--${tone}`}>
      <span className="status-workflow-icon" aria-hidden="true" />
      <div className="status-workflow-copy"><span>{label}</span><small>{detail}</small></div>
      <strong>{String(value).padStart(2, '0')}</strong>
    </div>
  )
}

function StatusSummaryMetric({ icon, label, value }: { icon: 'depth' | 'average' | 'response' | 'today'; label: string; value: string }) {
  return (
    <div className="status-summary-metric">
      <span className={`status-summary-metric-icon status-summary-metric-icon--${icon}`} aria-hidden="true" />
      <span className="status-summary-metric-label">{label}</span>
      <strong>{value}</strong>
    </div>
  )
}

export interface RainfallPanelProps {
  rainfall: RainfallSnapshot
  stationName?: string
  state?: PanelState
}

export function RainfallPanel({ rainfall, stationName = '徐家汇站', state = 'ready' }: RainfallPanelProps) {
  const chart = useMemo(() => {
    const chartWidth = 360
    const chartHeight = 112
    const max = Math.max(...rainfall.trend.map((item) => item.valueMmH), 100)
    const points = rainfall.trend.map((item, index) => {
      const x = (index / Math.max(rainfall.trend.length - 1, 1)) * chartWidth
      const y = chartHeight - (item.valueMmH / max) * (chartHeight - 16) - 4
      return { x, y, value: item.valueMmH }
    })
    return {
      points,
      line: points.map((point) => `${point.x},${point.y}`).join(' '),
      area: `0,${chartHeight} ${points.map((point) => `${point.x},${point.y}`).join(' ')} ${chartWidth},${chartHeight}`,
    }
  }, [rainfall.trend])

  return (
    <Panel className="rainfall-panel" state={state}>
      <PanelHeader
        title="实时雨情"
        icon="⌁"
        meta={
          <div className="rainfall-panel-tools">
            <span>更新于 {formatClock(rainfall.updatedAt)}</span>
            <button type="button" className="station-select">{stationName}<span>⌄</span></button>
          </div>
        }
      />
      <div className="rainfall-metrics">
        <MetricValue value={rainfall.intensityMmH.toFixed(1)} unit="mm/h" label="当前雨强" tone="cyan" />
        <MetricValue value={rainfall.cumulativeMm.toFixed(1)} unit="mm" label="累计雨量" tone="blue" />
        <MetricValue value={formatDuration(rainfall.durationMinutes)} unit="" label="持续时长" tone="white" compact />
      </div>
      <div className="chart-heading"><span>雨强趋势</span><small>(mm/h)</small></div>
      <div className="rainfall-chart" aria-label="最近 120 分钟雨强趋势图">
        <svg viewBox="0 0 360 144" preserveAspectRatio="none" role="img">
          <defs>
            <linearGradient id="rainArea" x1="0" x2="0" y1="0" y2="1">
              <stop offset="0" stopColor="#24d8ee" stopOpacity="0.35" />
              <stop offset="1" stopColor="#24d8ee" stopOpacity="0" />
            </linearGradient>
          </defs>
          {[0, 1, 2, 3].map((line) => <line key={line} x1="0" x2="360" y1={20 + line * 27} y2={20 + line * 27} className="chart-grid-line" />)}
          <polygon points={chart.area} fill="url(#rainArea)" />
          <polyline points={chart.line} fill="none" className="rain-line" />
          {chart.points.map((point, index) => (
            <circle key={`${point.x}-${index}`} cx={point.x} cy={point.y} r={index === chart.points.length - 1 ? 4.6 : 2.4} className={index === chart.points.length - 1 ? 'rain-point rain-point--current' : 'rain-point'} />
          ))}
          <text x="4" y="140" className="chart-axis-label">−120min</text>
          <text x="116" y="140" className="chart-axis-label">−90min</text>
          <text x="225" y="140" className="chart-axis-label">−60min</text>
          <text x="314" y="140" className="chart-axis-label">NOW</text>
           <text x="334" y={chart.points.at(-1)?.y ? chart.points.at(-1)!.y - 8 : 32} className="chart-current-label">{rainfall.intensityMmH.toFixed(1)}</text>
        </svg>
      </div>
    </Panel>
  )
}

function MetricValue({ value, unit, label, tone, compact = false }: { value: string; unit: string; label: string; tone: string; compact?: boolean }) {
  return (
    <div className={`metric-value metric-value--${tone} ${compact ? 'metric-value--compact' : ''}`}>
      <div><strong>{value}</strong>{unit && <small>{unit}</small>}</div>
      <span>{label}</span>
    </div>
  )
}

export interface RankingPanelProps {
  ranking: RainfallStationRankingItem[]
  state?: PanelState
}

export function RankingPanel({ ranking, state = 'ready' }: RankingPanelProps) {
  const rankedStations = [...ranking].sort((a, b) => b.intensityMmH - a.intensityMmH).slice(0, 5)
  const maxValue = Math.max(...rankedStations.map((station) => station.intensityMmH), 1)

  return (
    <Panel className="ranking-panel" state={state}>
      <PanelHeader title="重点区域雨强排行" icon="⌘" meta={<span>单位：mm/h</span>} />
      <div className="ranking-caption"><span>排名 / 站点</span><small>雨强</small></div>
      <div className="ranking-list">
        {rankedStations.map((station, index) => (
          <div className="ranking-row" key={station.stationId}>
            <span className={`rank-badge rank-badge--${index + 1}`}>{index + 1}</span>
            <span className="ranking-name" title={station.stationName}>{station.stationName.replace(/站$/, '')}</span>
            <span className="ranking-bar"><i style={{ width: `${(station.intensityMmH / maxValue) * 100}%` }} /></span>
            <strong className="ranking-value ranking-value--high">{station.intensityMmH.toFixed(1)}</strong>
          </div>
        ))}
      </div>
      <p className="panel-footnote">数据来源：Rainfall station ranking · 以雨强排序</p>
    </Panel>
  )
}

export interface EventPanelProps {
  event: FloodEvent | null
  analysis: AIAnalysis | null
  sensor?: SensorState | null
  sensorId?: string | null
  onOpenVision?: () => void
  state?: PanelState
}

export function EventPanel({ event, analysis, sensor = null, sensorId = null, onOpenVision, state = 'ready' }: EventPanelProps) {
  const [analysisOpen, setAnalysisOpen] = useState(false)
  if (!event) {
    return (
      <Panel className="event-panel" state={state === 'ready' ? 'empty' : state}>
        <PanelHeader title="内涝事件" icon="▮" meta={<span>未关联正式事件</span>} />
      </Panel>
    )
  }
  const durationMinutes = Math.round((event.durationSeconds ?? 0) / 60)

  return (
    <Panel className={`event-panel ${analysisOpen ? 'event-panel--expanded' : ''}`} state={state}>
      <PanelHeader title="内涝事件" icon="▮" meta={<span>事件 ID：{event.id}</span>} />
      <div className="event-title-row">
        <h3>{event.name}</h3>
        <div className="event-title-actions">
          <span className="risk-badge">{RISK_LABEL[event.riskLevel]}</span>
          {onOpenVision && <button type="button" className="vision-entry-button" onClick={onOpenVision}>VISION_IMAGE · 视觉水深证据</button>}
        </div>
      </div>
      <div className="event-metrics">
        <EventMetric label={sensor ? '实测水深' : '事件水深'} value={(sensor?.depthCm ?? event.currentDepthCm).toFixed(1)} unit="cm" />
        <EventMetric label="上涨速度" value={event.riseRateCmMin.toFixed(1)} unit="cm/min" />
        <EventMetric label="管网负荷" value={String(event.pipeLoadPercent)} unit="%" />
        <EventMetric label="风险等级" value={RISK_LABEL[event.riskLevel]} unit="" />
      </div>
      <div className="event-meta-grid">
        <span>所属区域 <strong>{event.district}</strong></span>
        <span>开始时间 <strong>{formatClock(event.startedAt)}</strong></span>
        <span>事件类型 <strong>{event.eventType}</strong></span>
        <span>持续时长 <strong>00:{String(durationMinutes).padStart(2, '0')}:41</strong></span>
      </div>
      <SensorEvidence sensor={sensor} sensorId={sensorId} />
      <AIAnalysisPanel analysis={analysis} expanded={analysisOpen} onToggle={() => setAnalysisOpen((open) => !open)} compact />
    </Panel>
  )
}

function EventMetric({ label, value, unit }: { label: string; value: string; unit: string }) {
  return <div className="event-metric"><span>{label}</span><strong>{value}<small>{unit}</small></strong></div>
}

export interface SensorEvidenceProps {
  sensor: SensorState | null
  sensorId?: string | null
}

type SensorFreshnessStatus = 'ONLINE' | 'STALE' | 'OFFLINE' | 'NO_EVIDENCE'

const SENSOR_STATUS_LABEL: Record<SensorFreshnessStatus, string> = {
  ONLINE: '在线',
  STALE: '延迟',
  OFFLINE: '离线',
  NO_EVIDENCE: '未上报',
}

function getSensorFreshness(sensor: SensorState | null): SensorFreshnessStatus {
  if (!sensor) return 'NO_EVIDENCE'
  const receivedAt = new Date(sensor.receivedAt).getTime()
  if (!Number.isFinite(receivedAt)) return 'OFFLINE'
  const ageMs = Date.now() - receivedAt
  if (ageMs > 30 * 60 * 1000) return 'OFFLINE'
  if (ageMs > 2 * 60 * 1000) return 'STALE'
  return 'ONLINE'
}

export function SensorEvidence({ sensor, sensorId = null }: SensorEvidenceProps) {
  const status = getSensorFreshness(sensor)

  if (!sensor) {
    return (
      <div className="sensor-evidence sensor-evidence--empty" role="status">
        <div className="sensor-evidence-head"><span>传感器状态</span><strong>{SENSOR_STATUS_LABEL[status]}</strong></div>
        {sensorId && <div className="sensor-evidence-grid"><span><small>对应传感器</small><b>{sensorId}</b></span></div>}
        <p>当前暂无实测数据</p>
      </div>
    )
  }

  return (
    <div className={`sensor-evidence sensor-evidence--${status.toLowerCase()}`}>
      <div className="sensor-evidence-head"><span>传感器状态</span><strong>{SENSOR_STATUS_LABEL[status]}</strong></div>
      <div className="sensor-evidence-grid">
        <span><small>sensorId</small><b>{sensor.sensorId}</b></span>
        <span><small>当前实测水深</small><b>{sensor.depthCm.toFixed(1)} cm</b></span>
        <span><small>最后上报</small><b>{formatClock(sensor.receivedAt)}</b></span>
      </div>
    </div>
  )
}

export interface SceneEventCardProps {
  event: FloodEvent | null
  analysis: AIAnalysis | null
  sensor?: SensorState | null
  sensorId?: string | null
}

export function SceneEventCard({ event, analysis, sensor = null, sensorId = null }: SceneEventCardProps) {
  if (!event) return null

  const sensorStatus = getSensorFreshness(sensor)
  const actions = analysis?.actions.slice().sort((left, right) => left.priority - right.priority).slice(0, 3) ?? []
  const currentDepthCm = sensor?.depthCm ?? event.currentDepthCm

  return (
    <article className={`scene-event-card scene-event-card--${event.riskLevel.toLowerCase()}`} aria-label="选中积水事件详情">
      <header className="scene-event-card-header">
        <div>
          <span className="scene-event-card-kicker">内涝事件</span>
          <h3>{formatSceneEventName(event.name)}</h3>
        </div>
        <span className={`scene-event-card-risk scene-event-card-risk--${event.riskLevel.toLowerCase()}`}>{RISK_LABEL[event.riskLevel]}</span>
      </header>

      <section className="scene-event-card-section scene-event-card-section--facts">
        <div className="scene-event-card-row"><span>位置</span><strong>{event.district} · {event.eventType}</strong></div>
        <div className="scene-event-card-row"><span>当前水深</span><strong className="scene-event-card-value--warning">{currentDepthCm.toFixed(1)} cm</strong></div>
        <div className="scene-event-card-row"><span>上涨速度</span><strong className="scene-event-card-value--warning">{event.riseRateCmMin.toFixed(1)} cm/min</strong></div>
      </section>

      <section className="scene-event-card-section">
        <h4>对应传感器</h4>
        <div className="scene-event-card-sensor-head">
          <strong>{sensor?.sensorId ?? sensorId ?? '未关联传感器'}</strong>
          <span className={`scene-event-card-sensor-status scene-event-card-sensor-status--${sensorStatus.toLowerCase()}`}>{SENSOR_STATUS_LABEL[sensorStatus]}</span>
        </div>
        {sensor ? (
          <div className="scene-event-card-sensor-grid">
            <div><span>当前实测水深</span><strong>{sensor.depthCm.toFixed(1)} cm</strong></div>
            <div><span>最后上报</span><strong>{formatClock(sensor.receivedAt)}</strong></div>
          </div>
        ) : <p className="scene-event-card-empty">当前暂无实测数据</p>}
      </section>

      <section className="scene-event-card-section scene-event-card-section--actions">
        <h4>处置建议</h4>
        <div className="scene-event-card-actions">
          {actions.length > 0 ? actions.map((action, index) => (
            <span className={`scene-event-card-action scene-event-card-action--${index + 1}`} key={`${action.priority}-${action.title}`}>{action.title}</span>
          )) : <span className="scene-event-card-empty">暂无处置建议</span>}
        </div>
      </section>
    </article>
  )
}

export interface ForecastPreviewProps {
  forecast: FloodForecast | null
  activeKey: ForecastKey
  onChange: (key: ForecastKey) => void
  measuredDepthCm?: number | null
  sourceLabel?: string
  state?: PanelState
}

export function ForecastPreview({ forecast, activeKey, onChange, measuredDepthCm = null, sourceLabel = 'SYNTHETIC FIXTURE', state = 'ready' }: ForecastPreviewProps) {
  if (!forecast) {
    return (
      <Panel className="forecast-panel" state={state === 'ready' ? 'empty' : state}>
        <PanelHeader title="内涝预测" icon="▮" meta={<span>当前点位未关联预测</span>} />
      </Panel>
    )
  }
  return (
    <Panel className="forecast-panel" state={state}>
      <PanelHeader title="内涝预测" icon="▮" meta={<span><b className="forecast-source-label">FORECAST · {sourceLabel}</b> <b className="help-dot">?</b></span>} />
      <div className="forecast-grid">
        {forecast.frames.map((frame) => (
          <button
            type="button"
            className={`forecast-card ${frame.timeKey === activeKey ? 'is-active' : ''}`}
            key={frame.timeKey}
            onClick={() => onChange(frame.timeKey)}
            aria-pressed={frame.timeKey === activeKey}
          >
            <span className="forecast-card-label">{FORECAST_LABEL[frame.timeKey]} <small>{frame.timeKey === 'NOW' ? 'SENSOR 实测' : 'FORECAST'}</small></span>
            <span className={`mini-map mini-map--${frame.timeKey.toLowerCase()}`}>
              <svg viewBox="0 0 120 78" aria-hidden="true">
                <path d="M42-8c-7 18-1 25 9 34 8 8 4 15-5 21-8 5-8 14-2 28" className="mini-river" />
                <path d={frame.timeKey === 'NOW' ? 'M27 45c8-13 19-16 32-11 8 3 19 3 31 14l-6 15-32 5-24-9Z' : frame.timeKey === 'PLUS_10' ? 'M18 35c13-14 27-13 39-7 14 7 24 6 43 14l-3 25-42 10-38-18Z' : 'M10 27c17-17 33-14 48-7 16 7 33 6 53 16l-2 31-54 10-47-25Z'} className="mini-flood" />
                <circle cx="62" cy="42" r="4" className="mini-marker" />
              </svg>
            </span>
            <span className="forecast-card-value">{(frame.timeKey === 'NOW' ? measuredDepthCm : frame.maxDepthCm)?.toFixed(1) ?? '—'}<small>cm</small></span>
          </button>
        ))}
      </div>
      <div className="forecast-summary"><span>水深(cm) · {activeKey === 'NOW' ? 'SENSOR 实测' : 'FORECAST 预测'}</span><strong>{(activeKey === 'NOW' ? measuredDepthCm : forecast.frames.find((frame) => frame.timeKey === activeKey)?.maxDepthCm)?.toFixed(1) ?? '—'} <small>{activeKey === 'NOW' ? 'measured baseline' : '当前预测帧最大水深'}</small></strong></div>
      <DepthLegend compact />
    </Panel>
  )
}

export interface CctvCardProps {
  camera: Camera | null
  state?: PanelState
  showOverlay?: boolean
  overlayData?: CctvOverlayData
  decision?: DecisionProjection | null
  videoEvidenceState?: VideoEvidenceState
  onVideoReady?: (ready: boolean) => void
  onVideoTimeUpdate?: (currentTimeSec: number) => void
}

export type CctvOverlayData = VideoOverlayData

export function CctvCard({ camera, state = 'ready', showOverlay = true, overlayData, decision = null, videoEvidenceState = 'missing', onVideoReady, onVideoTimeUpdate }: CctvCardProps) {
  const [playing, setPlaying] = useState(false)
  const [mediaState, setMediaState] = useState<'loading' | 'ready' | 'unavailable'>(camera?.mediaUrl ? 'loading' : 'unavailable')
  const videoRef = useRef<HTMLVideoElement>(null)

  useEffect(() => {
    setMediaState(camera?.mediaUrl ? 'loading' : 'unavailable')
    setPlaying(false)
    onVideoReady?.(false)
  }, [camera?.mediaUrl])

  if (!camera) {
    return (
      <Panel className="cctv-panel" state={state === 'ready' ? 'empty' : state}>
        <PanelHeader title="视频监控" icon="▮" meta={<span>VISION_VIDEO · 未关联摄像头</span>} />
      </Panel>
    )
  }

  const overlayStatusLabel = videoEvidenceState === 'loading'
    ? 'RESULT LOADING'
    : videoEvidenceState === 'error'
      ? 'RESULT NOT ATTACHED · FETCH FAILED'
      : videoEvidenceState === 'ready'
        ? overlayData
          ? `RESULT FRAME · ${overlayData.frameId}`
          : mediaState === 'ready' ? 'RESULT READY · NO FRAME' : 'RESULT READY · WAITING FOR MEDIA'
        : 'RESULT NOT ATTACHED'
  const researchVideo = camera.mediaUrl?.startsWith('/runtime/vision-video/') === true ||
    (overlayData?.runtimePolicy === 'research_mvp' && !overlayData.synthetic)
  const displayName = researchVideo ? '非实时视频' : camera.name
  const mediaStatusLabel = researchVideo ? '非实时视频' : camera.status
  const sourceLabel = researchVideo ? '视频证据 · 非实时' : `VISION_VIDEO · MEDIA / ${camera.mediaType}`
  const decisionDisplay = overlayData ? getDecisionDisplay(overlayData.floodDetected, decision) : null

  return (
    <Panel className="cctv-panel" state={state}>
      <PanelHeader title="视频监控" icon="▮" meta={<span>{displayName}</span>} />
      <div className={`cctv-viewport cctv-viewport--${mediaState}`} aria-label={`${displayName} 视频证据 seam`}>
        <video
          ref={videoRef}
          className="cctv-video"
          src={camera.mediaUrl || undefined}
          controls={mediaState === 'ready'}
          muted
          playsInline
          preload="metadata"
          onCanPlay={() => { setMediaState('ready'); onVideoReady?.(true) }}
          onLoadedData={() => { setMediaState('ready'); onVideoReady?.(true) }}
          onTimeUpdate={(event) => onVideoTimeUpdate?.(event.currentTarget.currentTime)}
          onError={() => { setMediaState('unavailable'); onVideoReady?.(false) }}
        />
        <div className="cctv-video-placeholder" />
        <div className="cctv-skyline" />
        <div className="cctv-road"><span className="road-lane road-lane--left" /><span className="road-lane road-lane--right" /></div>
        <div className="cctv-car cctv-car--one" /><div className="cctv-car cctv-car--two" /><div className="cctv-car cctv-car--three" />
        <div className="cctv-water-line" />
        {showOverlay && state === 'ready' && mediaState === 'ready' && overlayData?.waterMaskUrl && <img className="cctv-water-mask" src={overlayData.waterMaskUrl} alt="" aria-hidden="true" />}
        {showOverlay && state === 'ready' && mediaState === 'ready' && overlayData?.objects?.map((object, index) => (
          <span
            className={`cctv-box cctv-box--${object.type}`}
            key={`${object.type}-${index}`}
            style={{ left: `${object.left}%`, top: `${object.top}%`, width: `${object.width}%`, height: `${object.height}%` }}
          >
            {object.type}
          </span>
        ))}
        <span className="cctv-source-tag">{mediaState === 'ready' ? sourceLabel : 'VISION_VIDEO · DEMO / PLACEHOLDER'}</span>
        <span className="cctv-overlay-status">{overlayStatusLabel}</span>
        {showOverlay && state === 'ready' && mediaState === 'ready' && overlayData && decisionDisplay && <div className="cctv-decision-strip" aria-label="视频决策结论">
          <div><small>检测结论</small><b>{decisionDisplay.conclusion}</b></div>
          <div><small>估计水深</small><b>{decisionDisplay.depth}</b></div>
          <div><small>通行状态</small><b>{decisionDisplay.trafficStatus}</b></div>
          <p>行动建议：{decisionDisplay.recommendation}</p>
        </div>}
        {showOverlay && state === 'ready' && mediaState === 'ready' && overlayData && <details className="cctv-tech-details">
          <summary>技术详情</summary>
          <dl>
            <div><dt>sourceType</dt><dd>{overlayData.sourceType}</dd></div>
            <div><dt>sourceId</dt><dd>{overlayData.sourceId}</dd></div>
            <div><dt>runtimePolicy</dt><dd>{overlayData.runtimePolicy}</dd></div>
            <div><dt>licenseReview</dt><dd>{overlayData.licenseReview}</dd></div>
            <div><dt>frame</dt><dd>{overlayData.frameId} · t={overlayData.timestampMs}ms</dd></div>
            <div><dt>rangeCm</dt><dd>{formatRangeCm(overlayData.rangeCm)}</dd></div>
            <div><dt>estimatedDepthCm</dt><dd>{overlayData.estimatedDepthCm === null ? 'null' : `${overlayData.estimatedDepthCm.toFixed(1)} cm`}</dd></div>
            <div><dt>quality</dt><dd>{overlayData.quality} · {overlayData.qualityFlags.join(' · ') || 'none'}</dd></div>
          </dl>
        </details>}
        <span className={`cctv-media-status cctv-media-status--${mediaState}`}><i />{mediaState === 'ready' ? mediaStatusLabel : mediaState === 'loading' ? 'MEDIA CHECKING' : `${mediaStatusLabel} · PLACEHOLDER`}</span>
        {state === 'empty' && <span className="cctv-empty-copy">fixture 已提供媒体路径，当前未发现合法本地媒体</span>}
      </div>
      <div className="cctv-controls">
        <button
          type="button"
          className="cctv-play"
          disabled={mediaState !== 'ready'}
          onClick={() => {
            const video = videoRef.current
            if (!video || mediaState !== 'ready') return
            if (video.paused) {
              void video.play()
              setPlaying(true)
            } else {
              video.pause()
              setPlaying(false)
            }
          }}
          aria-label={playing ? '暂停视频' : '播放视频'}
        >{playing ? 'Ⅱ' : '▶'}</button>
        <span className="cctv-camera-name">{displayName}</span>
        <div className="cctv-legend"><span><i className="legend-color legend-color--water" />积水区域</span><span><i className="legend-color legend-color--vehicle" />车辆</span><span><i className="legend-color legend-color--person" />行人</span></div>
      </div>
    </Panel>
  )
}

export interface VisionDepthDrawerProps {
  open: boolean
  mode: 'local' | 'url'
  sourceValue: string
  sourcePreviewUrl?: string | null
  fileName?: string
  state: 'idle' | 'loading' | 'error' | 'ready'
  errorMessage?: string | null
  observation: VisionDepthObservation | null
  onClose: () => void
  onModeChange: (mode: 'local' | 'url') => void
  onSourceChange: (value: string) => void
  onFileChange: (file: File | null) => void
  onAnalyze: () => void
}

const VISION_METHOD_LABEL: Record<VisionDepthObservation['method'], string> = {
  VISUAL_RANGE: '视觉范围',
  NO_REFERENCE: '无参考物',
  PERSON_REFERENCE: '人员参考物',
  VEHICLE_REFERENCE: '车辆参考物',
  TRAFFIC_SIGN_REFERENCE: '交通标志参考物',
  FIXED_CAMERA_REFERENCE: '固定摄像头参考物',
}

function resolveVisionMediaUrl(path: string | null | undefined): string | null {
  if (!path) return null
  if (/^https?:\/\//.test(path)) return path
  if (path.startsWith('/api/')) return `${API_BASE_URL}${path}`
  if (path.startsWith('/')) return path
  return null
}

function formatVisionRange(range: VisionDepthObservation['depth']['rangeCm']): string {
  const [minimum, maximum] = range
  if (minimum === null) return maximum === null ? '—' : `≤${maximum} cm`
  if (maximum === null) return `≥${minimum} cm`
  return `${minimum}–${maximum} cm`
}

interface DecisionDisplay {
  conclusion: string
  depth: string
  trafficStatus: string
  recommendation: string
}

const TRAFFIC_STATUS_LABELS: Record<string, string> = {
  NORMAL: '正常通行',
  NORMAL_PASSAGE: '正常通行',
  CAUTION: '谨慎通行',
  CAUTION_PASSAGE: '谨慎通行',
  NOT_RECOMMENDED: '不建议通行',
  DO_NOT_PASS: '不建议通行',
  PROHIBITED: '禁止通行',
  NO_PASSAGE: '禁止通行',
  正常通行: '正常通行',
  谨慎通行: '谨慎通行',
  不建议通行: '不建议通行',
  禁止通行: '禁止通行',
}

const RECOMMENDATION_BY_TRAFFIC_STATUS: Record<string, string> = {
  正常通行: '可维持通行，继续关注现场变化',
  谨慎通行: '建议减速观察，必要时临时管控',
  不建议通行: '建议限制通行并加强现场处置',
  禁止通行: '积水较深，建议立即封控并组织排水',
}

function normalizeTrafficStatus(value: string | undefined): string {
  const candidate = value?.trim() ?? ''
  if (!candidate) return '待判定'
  return TRAFFIC_STATUS_LABELS[candidate] ?? TRAFFIC_STATUS_LABELS[candidate.toUpperCase()] ?? '待判定'
}

function isUsableRecommendation(value: string | undefined): value is string {
  const candidate = value?.trim() ?? ''
  return Boolean(candidate)
    && /[\u4e00-\u9fff]/.test(candidate)
    && !/(粗略|视觉估计|当前证据不足|待水深标定|仅供初筛|不等同|传感器实测|等待行动建议|待判定|暂无)/.test(candidate)
    && !/(confidence|quality|source|rough|visual estimate)/i.test(candidate)
}

function getDecisionDisplay(floodDetected: boolean, decision?: DecisionProjection | null): DecisionDisplay {
  const decisionDepth = decision?.decisionDepthCm
  const depth = typeof decisionDepth === 'number' && Number.isFinite(decisionDepth)
    ? `约 ${decisionDepth.toFixed(0)} cm`
    : '待形成'
  const trafficStatus = normalizeTrafficStatus(decision?.trafficStatus)
  const recommendation = isUsableRecommendation(decision?.recommendation)
    ? decision.recommendation.trim()
    : RECOMMENDATION_BY_TRAFFIC_STATUS[trafficStatus] ?? (floodDetected ? '请结合现场情况处置' : '保持常规巡检')

  return {
    conclusion: floodDetected ? '检测到积水' : '未检测到积水',
    depth,
    trafficStatus,
    recommendation,
  }
}

export function VisionDepthDrawer({
  open,
  mode,
  sourceValue,
  sourcePreviewUrl = null,
  fileName,
  state,
  errorMessage,
  observation,
  onClose,
  onModeChange,
  onSourceChange,
  onFileChange,
  onAnalyze,
}: VisionDepthDrawerProps) {
  const [mediaView, setMediaView] = useState<'result' | 'original' | 'mask'>('result')
  const originalUrl = sourcePreviewUrl ?? (mode === 'url' ? sourceValue : '')
  const maskUrl = resolveVisionMediaUrl(observation?.waterMaskPath)
  const range = observation?.depth.rangeCm ?? [null, null]
  const decisionDisplay = observation ? getDecisionDisplay(observation.floodDetected, observation.decision) : null
  const calibrationLabel = observation?.qualityFlags.includes('CAMERA_UNCALIBRATED')
    ? '未标定（CAMERA_UNCALIBRATED）'
    : '当前 Contract 未显式提供 CameraProfile 标定状态'

  useEffect(() => {
    if (observation?.imageId) setMediaView('result')
  }, [observation?.imageId])

  if (!open) return null

  return (
    <aside className="vision-drawer" aria-label="VisionDepth 水深证据抽屉">
      <div className="vision-drawer-head">
        <div><span className="vision-drawer-kicker">VISION_IMAGE · AI EVIDENCE</span><h2>图像积水识别</h2></div>
        <button type="button" className="vision-close" onClick={onClose} aria-label="关闭视觉水深证据">×</button>
      </div>
      <div className="vision-source-tabs" role="tablist" aria-label="视觉证据来源">
        <button type="button" role="tab" aria-selected={mode === 'local'} className={mode === 'local' ? 'is-active' : ''} onClick={() => onModeChange('local')}>本地上传</button>
        <button type="button" role="tab" aria-selected={mode === 'url'} className={mode === 'url' ? 'is-active' : ''} onClick={() => onModeChange('url')}>直接 URL</button>
      </div>
      <div className="vision-source-form">
        {mode === 'local' ? (
          <label className="vision-file-input">选择图片<input key="local-image" type="file" accept="image/*" onChange={(event) => onFileChange(event.target.files?.[0] ?? null)} /></label>
        ) : (
          <label className="vision-url-input">图片 URL<input key="direct-url" type="url" value={sourceValue} onChange={(event) => onSourceChange(event.target.value)} placeholder="https://…" /></label>
        )}
        <button type="button" className="vision-analyze-button" onClick={onAnalyze} disabled={state === 'loading' || (mode === 'local' ? !fileName : !sourceValue.trim())}>{state === 'loading' ? '读取中…' : '读取证据'}</button>
      </div>
      {fileName && <p className="vision-source-name">source=VISION_IMAGE · local · {fileName}</p>}
      {state === 'error' && <p className="vision-state vision-state--error" role="alert">{errorMessage ?? 'VisionDepth 读取失败'}</p>}
      {state === 'loading' && <p className="vision-state" role="status">正在等待 VisionDepth Observation；不会覆盖 NOW 实测水深。</p>}

      {observation && decisionDisplay && (
        <section className={`vision-business-card ${observation.floodDetected ? 'is-flood' : 'is-clear'}`} aria-label="图像积水业务结论">
          <div className="vision-business-status"><i />{decisionDisplay.conclusion}</div>
          <div className="vision-business-depth"><span>估计水深</span><strong>{decisionDisplay.depth}</strong></div>
          <div className="vision-passability">
            <span>通行状态</span>
            <b>{decisionDisplay.trafficStatus}</b>
            <small>行动建议：{decisionDisplay.recommendation}</small>
          </div>
        </section>
      )}

      <div className="vision-media-tabs" role="tablist" aria-label="AI结果、原图与水体Mask">
        <button type="button" role="tab" aria-selected={mediaView === 'result'} className={mediaView === 'result' ? 'is-active' : ''} onClick={() => setMediaView('result')}>AI结果</button>
        <button type="button" role="tab" aria-selected={mediaView === 'original'} className={mediaView === 'original' ? 'is-active' : ''} onClick={() => setMediaView('original')}>原图</button>
        <button type="button" role="tab" aria-selected={mediaView === 'mask'} className={mediaView === 'mask' ? 'is-active' : ''} onClick={() => setMediaView('mask')}>水体Mask</button>
      </div>
      <div className={`vision-media-preview vision-media-preview--${mediaView}`}>
        {mediaView === 'result' && observation && originalUrl ? (
          <div className="vision-ai-result">
            <img className="vision-ai-original" src={originalUrl} alt="VisionDepth AI 识别结果原图" onError={(event) => { event.currentTarget.style.display = 'none' }} />
            {maskUrl && <img className="vision-ai-mask" src={maskUrl} alt="" aria-hidden="true" onError={(event) => { event.currentTarget.style.display = 'none' }} />}
            <span className="vision-ai-result-label">AI RESULT · {maskUrl ? 'WATER MASK OVERLAY' : 'MASK NOT ATTACHED'}</span>
          </div>
        ) : null}
        {mediaView === 'original' && originalUrl ? <img src={originalUrl} alt="VisionDepth 原始图像" onError={(event) => { event.currentTarget.style.display = 'none' }} /> : null}
        {mediaView === 'mask' && maskUrl ? <img src={maskUrl} alt="VisionDepth 水域掩膜" onError={(event) => { event.currentTarget.style.display = 'none' }} /> : null}
        {mediaView === 'mask' && observation && !maskUrl && <div className="vision-media-unavailable"><strong>MASK PATH · NOT ATTACHED</strong><code>{observation.waterMaskPath}</code></div>}
        {((mediaView === 'result' && (!observation || !originalUrl)) || (mediaView === 'original' && !originalUrl) || (mediaView === 'mask' && !observation)) && <div className="vision-media-unavailable">等待 {mediaView === 'result' ? 'AI result' : mediaView === 'original' ? 'original' : 'mask'} evidence</div>}
      </div>

      {observation ? (
        <div className="vision-observation" data-quality={observation.quality}>
          <div className="vision-observation-head"><span>证据边界</span><strong>{observation.synthetic ? 'DEMO / SYNTHETIC' : 'VISION_IMAGE'}</strong></div>
          <details className="vision-tech-details">
            <summary>技术详情</summary>
            <dl className="vision-observation-meta">
              <div><dt>imageId</dt><dd>{observation.imageId}</dd></div>
              <div><dt>sourceId</dt><dd>{observation.provenance.sourceId}</dd></div>
              <div><dt>sourceType</dt><dd>{observation.provenance.sourceType}</dd></div>
              <div><dt>method</dt><dd>{VISION_METHOD_LABEL[observation.method]}</dd></div>
              <div><dt>level</dt><dd>{observation.depth.level}</dd></div>
              <div><dt>approximateDepthCm</dt><dd>{observation.depth.approximateDepthCm == null ? 'null' : `${observation.depth.approximateDepthCm.toFixed(1)} cm · rough`}</dd></div>
              <div><dt>rangeCm</dt><dd>{formatVisionRange(range)}</dd></div>
              <div><dt>referenceObjects</dt><dd><code>{JSON.stringify(observation.referenceObjects)}</code></dd></div>
              <div><dt>quality</dt><dd>{observation.quality}</dd></div>
              <div><dt>qualityFlags</dt><dd>{observation.qualityFlags.length ? observation.qualityFlags.join(' · ') : 'none'}</dd></div>
              <div><dt>model</dt><dd><code>{JSON.stringify(observation.model)}</code></dd></div>
              <div><dt>camera calibration</dt><dd>{calibrationLabel}</dd></div>
              <div><dt>runtimePolicy</dt><dd>{observation.provenance.runtimePolicy}</dd></div>
              <div><dt>licenseReview</dt><dd>{observation.provenance.licenseReview}</dd></div>
              <div><dt>waterMaskPath</dt><dd><code>{observation.waterMaskPath}</code></dd></div>
            </dl>
          </details>
        </div>
      ) : <div className="vision-observation-empty">尚未产生 VisionDepthObservation。</div>}
    </aside>
  )
}

export interface LayerVisibility {
  base: boolean
  water: boolean
  depth: boolean
  network: boolean
  video: boolean
  measure: boolean
}

export interface LayerToolbarProps {
  layers: LayerVisibility
  onToggle: (layer: keyof LayerVisibility) => void
}

export function LayerToolbar({ layers, onToggle }: LayerToolbarProps) {
  const layerItems: Array<{ key: keyof LayerVisibility; label: string; glyph: string }> = [
    { key: 'base', label: '图层', glyph: '▰' },
    { key: 'water', label: '水系', glyph: '◊' },
    { key: 'depth', label: '水深', glyph: '◉' },
    { key: 'network', label: '管网', glyph: '⌘' },
    { key: 'video', label: '视频', glyph: '▣' },
    { key: 'measure', label: '测距', glyph: '↔' },
  ]

  return (
    <div className="layer-toolbar" aria-label="图层工具栏">
      {layerItems.map((item) => (
        <button type="button" className={`layer-tool ${layers[item.key] ? 'is-on' : ''}`} key={item.key} onClick={() => onToggle(item.key)} aria-pressed={layers[item.key]}>
          <span>{item.glyph}</span><small>{item.label}</small>
        </button>
      ))}
    </div>
  )
}

export interface DigitalTwinSceneProps {
  event: FloodEvent | null
  points: FloodPoint[]
  sensor?: SensorState | null
  activeForecast: ForecastKey
  forecastFrame?: ForecastFrame | null
  selectedPointId: string
  layers: LayerVisibility
  onPointSelect: (id: string) => void
  onLayerToggle: (layer: keyof LayerVisibility) => void
  compact?: boolean
}

export function DigitalTwinScene({ event, points, sensor = null, activeForecast, forecastFrame = null, selectedPointId, layers, onPointSelect, onLayerToggle, compact = false }: DigitalTwinSceneProps) {
  return (
    <section className={`digital-twin-scene ${compact ? 'digital-twin-scene--compact' : ''}`} aria-label="上海数字孪生场景">
      <CesiumScene
        event={event}
        points={points}
        sensor={sensor}
        activeForecast={activeForecast}
        forecastFrame={forecastFrame}
        selectedPointId={selectedPointId}
        layers={layers}
        onPointSelect={onPointSelect}
      />
      <div className="scene-atmosphere" />
      <div className="scene-label scene-label--top"><span className="scene-status-dot" />SHANGHAI DIGITAL TWIN <small>CESIUM CITY · L1</small></div>
      <div className="scene-label scene-label--bottom">中心场景：{FORECAST_LABEL[activeForecast]} · {activeForecast === 'NOW' ? '当前实测基准' : '预测积水范围更新中'}</div>
      <div className="scene-toolbar-wrap"><LayerToolbar layers={layers} onToggle={onLayerToggle} /></div>
      <div className="scene-depth-legend"><DepthLegend /></div>
    </section>
  )
}

export function DepthLegend({ compact = false }: { compact?: boolean }) {
  return (
    <div className={`depth-legend ${compact ? 'depth-legend--compact' : ''}`} aria-label="水深图例">
      <div className="depth-legend-title">水深(cm)</div>
      <div className="depth-legend-scale"><i /></div>
      <div className="depth-legend-labels"><span>0</span><span>10</span><span>20</span><span>30</span><span>50</span><span>80</span><span>100+</span></div>
    </div>
  )
}

export interface TimelineBarProps {
  timeline: ScenarioTimeline
  activeKey: ForecastKey
  onForecastChange: (key: ForecastKey) => void
}

export function TimelineBar({ timeline, activeKey, onForecastChange }: TimelineBarProps) {
  const [playing, setPlaying] = useState(false)
  const [hour, setHour] = useState(10.4)

  return (
    <section className="timeline-bar" aria-label="场景时间轴">
      <button type="button" className={`timeline-play ${playing ? 'is-playing' : ''}`} onClick={() => setPlaying((value) => !value)} aria-label={playing ? '暂停时间轴' : '播放时间轴'}>{playing ? 'Ⅱ' : '▶'}</button>
      <button type="button" className="timeline-speed" onClick={() => setPlaying((value) => !value)}>1x <span>⌄</span></button>
      <div className="timeline-date"><span>{formatDate(timeline.currentTime)}</span><span className="calendar-glyph">▣</span></div>
      <div className="timeline-track-wrap">
        <div className="timeline-track-label"><span>场景时间</span><strong>{formatClock(timeline.currentTime).slice(0, 5)}</strong></div>
        <input type="range" min="0" max="24" step="0.1" value={hour} onChange={(event) => setHour(Number(event.target.value))} className="timeline-range" aria-label="场景时间定位" />
        <div className="timeline-hours"><span>00:00</span><span>02:00</span><span>04:00</span><span>06:00</span><span>08:00</span><span>10:00</span><span>12:00</span><span>14:00</span><span>16:00</span><span>18:00</span><span>20:00</span><span>22:00</span><span>24:00</span></div>
      </div>
      <div className="timeline-forecast-switcher" role="group" aria-label="预测时间状态">
        {(['NOW', 'PLUS_10', 'PLUS_30'] as ForecastKey[]).map((key) => <button key={key} type="button" className={key === activeKey ? 'is-active' : ''} onClick={() => onForecastChange(key)}>{FORECAST_LABEL[key]}</button>)}
      </div>
      <span className="timeline-mode">{timeline.mode === 'PLAYBACK' ? '回放' : activeKey === 'NOW' ? '实时' : '预测'}</span>
    </section>
  )
}

export interface AIAnalysisPanelProps {
  analysis: AIAnalysis | null
  expanded?: boolean
  compact?: boolean
  onToggle?: () => void
}

export function AIAnalysisPanel({ analysis, expanded = false, compact = false, onToggle }: AIAnalysisPanelProps) {
  const [localOpen, setLocalOpen] = useState(expanded)
  const isOpen = onToggle ? expanded : localOpen
  const toggle = onToggle ?? (() => setLocalOpen((value) => !value))

  if (!analysis) {
    return (
      <section className={`analysis-panel ${compact ? 'analysis-panel--compact' : ''}`}>
        <button type="button" className="analysis-toggle" disabled>
          <span><i className="analysis-spark" />AI 研判</span><strong>未关联</strong>
        </button>
        <p className="analysis-summary">当前点位暂无正式事件研判。</p>
      </section>
    )
  }

  return (
    <section className={`analysis-panel ${compact ? 'analysis-panel--compact' : ''} ${isOpen ? 'is-open' : ''}`}>
      <button type="button" className="analysis-toggle" onClick={toggle} aria-expanded={isOpen}>
        <span><i className="analysis-spark" />AI 研判</span><strong>{isOpen ? '收起' : '展开'} <span>{isOpen ? '⌃' : '⌄'}</span></strong>
      </button>
      <p className="analysis-summary">{analysis.riskSummary}</p>
      {isOpen && (
        <div className="analysis-details">
          <div className="analysis-causes"><h4>主要原因</h4>{analysis.causes.map((cause) => <span key={cause.label}><i style={{ width: `${cause.weight * 100}%` }} />{cause.label}<b>{Math.round(cause.weight * 100)}%</b></span>)}</div>
          <p className="analysis-forecast"><b>预测</b>{analysis.forecastSummary}</p>
          <div className="analysis-actions"><h4>处置建议</h4>{analysis.actions.map((action) => <span key={action.priority}><b>{action.priority}</b>{action.title}</span>)}</div>
        </div>
      )}
    </section>
  )
}
