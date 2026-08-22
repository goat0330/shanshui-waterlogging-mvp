import { useMemo, useState, type CSSProperties, type ReactNode } from 'react'
import type {
  AIAnalysis,
  Camera,
  DashboardOverview,
  FloodEvent,
  FloodForecast,
  FloodPoint,
  ForecastFrame,
  ForecastKey,
  PanelState,
  RainfallSnapshot,
  RainfallStationRankingItem,
  ScenarioTimeline,
} from './types'
import { CesiumScene } from './CesiumScene'

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

function formatDate(value: string) {
  const date = new Date(value)
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
}

function formatDuration(minutes = 0) {
  const hours = Math.floor(minutes / 60)
  const remainder = minutes % 60
  return `${hours} h ${remainder.toString().padStart(2, '0')} min`
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
  const { critical, warning, normal } = overview.urbanStatus
  const total = Math.max(critical + warning + normal, 1)
  const criticalEnd = (critical / total) * 100
  const warningEnd = ((critical + warning) / total) * 100
  const ringStyle = {
    background: `conic-gradient(var(--critical) 0 ${criticalEnd}%, var(--warning) ${criticalEnd}% ${warningEnd}%, var(--cyan) ${warningEnd}% 100%)`,
  } as CSSProperties

  return (
    <Panel className={`status-panel ${variant === 'high-risk' ? 'status-panel--high-risk' : ''}`} state={state}>
      <PanelHeader title="城市态势" icon="◈" meta={<span>更新于 {formatClock(overview.updatedAt)}</span>} />
      <div className="status-content">
        <div className="status-ring" style={ringStyle} aria-label={`严重 ${critical}，警戒 ${warning}，正常 ${normal}`}>
          <div className="status-ring-hole">
            <span className="cloud-glyph">☁</span>
            <span className="cloud-rain">···</span>
          </div>
        </div>
        <div className="status-list">
          <StatusRow label="严重" count={critical} detail="涉及区域" tone="critical" />
          <StatusRow label="警戒" count={warning} detail="涉及区域" tone="warning" />
          <StatusRow label="正常" count={normal} detail="涉及区域" tone="normal" />
        </div>
      </div>
    </Panel>
  )
}

function StatusRow({ label, count, detail, tone }: { label: string; count: number; detail: string; tone: string }) {
  return (
    <div className={`status-row status-row--${tone}`}>
      <span className="status-row-icon">{tone === 'critical' ? '◆' : tone === 'warning' ? '◆' : '◉'}</span>
      <span className="status-row-copy"><strong>{label}</strong><small>{detail} {count}</small></span>
      <strong className="status-row-value">{String(count).padStart(2, '0')}</strong>
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
  state?: PanelState
}

export function EventPanel({ event, analysis, state = 'ready' }: EventPanelProps) {
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
        <span className="risk-badge">{RISK_LABEL[event.riskLevel]}</span>
      </div>
      <div className="event-metrics">
        <EventMetric label="当前水深" value={event.currentDepthCm.toFixed(1)} unit="cm" />
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
      <AIAnalysisPanel analysis={analysis} expanded={analysisOpen} onToggle={() => setAnalysisOpen((open) => !open)} compact />
    </Panel>
  )
}

function EventMetric({ label, value, unit }: { label: string; value: string; unit: string }) {
  return <div className="event-metric"><span>{label}</span><strong>{value}<small>{unit}</small></strong></div>
}

export interface ForecastPreviewProps {
  forecast: FloodForecast | null
  activeKey: ForecastKey
  onChange: (key: ForecastKey) => void
  state?: PanelState
}

export function ForecastPreview({ forecast, activeKey, onChange, state = 'ready' }: ForecastPreviewProps) {
  if (!forecast) {
    return (
      <Panel className="forecast-panel" state={state === 'ready' ? 'empty' : state}>
        <PanelHeader title="内涝预测" icon="▮" meta={<span>当前点位未关联预测</span>} />
      </Panel>
    )
  }
  return (
    <Panel className="forecast-panel" state={state}>
      <PanelHeader title="内涝预测" icon="▮" meta={<span>未来变化趋势 <b className="help-dot">?</b></span>} />
      <div className="forecast-grid">
        {forecast.frames.map((frame) => (
          <button
            type="button"
            className={`forecast-card ${frame.timeKey === activeKey ? 'is-active' : ''}`}
            key={frame.timeKey}
            onClick={() => onChange(frame.timeKey)}
            aria-pressed={frame.timeKey === activeKey}
          >
            <span className="forecast-card-label">{FORECAST_LABEL[frame.timeKey]}</span>
            <span className={`mini-map mini-map--${frame.timeKey.toLowerCase()}`}>
              <svg viewBox="0 0 120 78" aria-hidden="true">
                <path d="M42-8c-7 18-1 25 9 34 8 8 4 15-5 21-8 5-8 14-2 28" className="mini-river" />
                <path d={frame.timeKey === 'NOW' ? 'M27 45c8-13 19-16 32-11 8 3 19 3 31 14l-6 15-32 5-24-9Z' : frame.timeKey === 'PLUS_10' ? 'M18 35c13-14 27-13 39-7 14 7 24 6 43 14l-3 25-42 10-38-18Z' : 'M10 27c17-17 33-14 48-7 16 7 33 6 53 16l-2 31-54 10-47-25Z'} className="mini-flood" />
                <circle cx="62" cy="42" r="4" className="mini-marker" />
              </svg>
            </span>
            <span className="forecast-card-value">{frame.maxDepthCm.toFixed(1)}<small>cm</small></span>
          </button>
        ))}
      </div>
      <div className="forecast-summary"><span>水深(cm)</span><strong>{forecast.frames.find((frame) => frame.timeKey === activeKey)?.maxDepthCm.toFixed(1)} <small>当前帧最大水深</small></strong></div>
      <DepthLegend compact />
    </Panel>
  )
}

export interface CctvCardProps {
  camera: Camera | null
  state?: PanelState
  showOverlay?: boolean
  overlayData?: CctvOverlayData
}

export interface CctvOverlayData {
  waterDepthCm?: number
  objects?: Array<{
    type: 'vehicle' | 'person'
    left: number
    top: number
    width: number
    height: number
  }>
}

const DEFAULT_CCTV_OVERLAY: CctvOverlayData = {
  waterDepthCm: 28.6,
  objects: [
    { type: 'vehicle', left: 30, top: 44, width: 17, height: 31 },
    { type: 'person', left: 70, top: 33, width: 8, height: 34 },
  ],
}

export function CctvCard({ camera, state = 'ready', showOverlay = true, overlayData = DEFAULT_CCTV_OVERLAY }: CctvCardProps) {
  const [playing, setPlaying] = useState(false)
  if (!camera) {
    return (
      <Panel className="cctv-panel" state={state === 'ready' ? 'empty' : state}>
        <PanelHeader title="视频监控" icon="▮" meta={<span>未关联摄像头</span>} />
      </Panel>
    )
  }

  return (
    <Panel className="cctv-panel" state={state}>
      <PanelHeader title="视频监控" icon="▮" meta={<span>{camera.name}</span>} />
      <div className="cctv-viewport" aria-label="CCTV 演示占位画面">
        <div className="cctv-video-placeholder" />
        <div className="cctv-skyline" />
        <div className="cctv-road"><span className="road-lane road-lane--left" /><span className="road-lane road-lane--right" /></div>
        <div className="cctv-car cctv-car--one" /><div className="cctv-car cctv-car--two" /><div className="cctv-car cctv-car--three" />
        <div className="cctv-water-line" />
        {showOverlay && state === 'ready' && overlayData.objects?.map((object, index) => (
          <span
            className={`cctv-box cctv-box--${object.type}`}
            key={`${object.type}-${index}`}
            style={{ left: `${object.left}%`, top: `${object.top}%`, width: `${object.width}%`, height: `${object.height}%` }}
          >
            {object.type}
          </span>
        ))}
        {showOverlay && state === 'ready' && <span className="cctv-depth-tag">WATER {overlayData.waterDepthCm?.toFixed(1) ?? '--'} cm</span>}
        <span className="cctv-source-tag">{state === 'ready' ? 'DEMO FEED · 场景占位' : 'MEDIA NOT ATTACHED'}</span>
        <span className={`cctv-live ${camera.status === 'ONLINE' ? 'cctv-live--demo' : 'cctv-live--offline'}`}><i />{camera.status === 'ONLINE' ? 'DEMO LIVE' : camera.status}</span>
        {state === 'empty' && <span className="cctv-empty-copy">fixture 已提供路径，待本地 MP4 接入</span>}
      </div>
      <div className="cctv-controls">
        <button type="button" className="cctv-play" onClick={() => setPlaying((value) => !value)} aria-label={playing ? '暂停演示视频' : '播放演示视频'}>{playing ? 'Ⅱ' : '▶'}</button>
        <span className="cctv-camera-name">{camera.name}</span>
        <div className="cctv-legend"><span><i className="legend-color legend-color--water" />积水区域</span><span><i className="legend-color legend-color--vehicle" />车辆</span><span><i className="legend-color legend-color--person" />行人</span></div>
      </div>
    </Panel>
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
  activeForecast: ForecastKey
  forecastFrame?: ForecastFrame | null
  selectedPointId: string
  layers: LayerVisibility
  onPointSelect: (id: string) => void
  onLayerToggle: (layer: keyof LayerVisibility) => void
  compact?: boolean
}

export function DigitalTwinScene({ event, points, activeForecast, forecastFrame = null, selectedPointId, layers, onPointSelect, onLayerToggle, compact = false }: DigitalTwinSceneProps) {
  return (
    <section className={`digital-twin-scene ${compact ? 'digital-twin-scene--compact' : ''}`} aria-label="上海数字孪生场景">
      <CesiumScene
        event={event}
        points={points}
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
