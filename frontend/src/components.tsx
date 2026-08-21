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

const MARKER_POSITIONS: Record<string, { x: number; y: number }> = {
  'FP-001': { x: 608, y: 444 },
  'FP-002': { x: 508, y: 553 },
  'FP-003': { x: 560, y: 575 },
  'FP-004': { x: 723, y: 531 },
  'FP-005': { x: 684, y: 337 },
}

const BUILDINGS = [
  [106, 166, 42, 110], [160, 204, 32, 86], [203, 142, 34, 135],
  [248, 232, 52, 96], [320, 177, 39, 118], [368, 248, 58, 128],
  [434, 141, 34, 102], [478, 211, 46, 144], [532, 174, 32, 106],
  [585, 235, 40, 132], [630, 151, 52, 112], [696, 206, 38, 126],
  [752, 175, 55, 94], [818, 231, 44, 134], [871, 150, 33, 112],
  [148, 362, 44, 127], [204, 407, 35, 83], [252, 348, 49, 148],
  [319, 407, 34, 97], [374, 362, 58, 123], [450, 399, 40, 78],
  [504, 343, 34, 140], [554, 392, 52, 101], [623, 353, 41, 118],
  [680, 414, 58, 84], [758, 360, 35, 120], [812, 402, 48, 96],
  [866, 340, 36, 142], [118, 522, 50, 83], [181, 548, 38, 112],
  [237, 502, 44, 98], [302, 557, 52, 70], [385, 514, 35, 110],
  [440, 559, 50, 87], [520, 505, 38, 107], [578, 553, 45, 76],
  [652, 515, 52, 91], [725, 560, 39, 76], [780, 504, 55, 111],
  [858, 545, 45, 85],
] as const

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

function formatSceneDepth(event: FloodEvent | null, selectedPoint: FloodPoint | null, activeForecast: ForecastKey, forecastFrame: ForecastFrame | null | undefined) {
  const depth = activeForecast === 'NOW' ? event?.currentDepthCm ?? selectedPoint?.depthCm : forecastFrame?.maxDepthCm
  return depth === undefined ? '--' : depth.toFixed(1)
}

function SvgSceneFallback({ event, points, activeForecast, forecastFrame = null, selectedPointId, layers, onPointSelect, onLayerToggle, compact = false }: DigitalTwinSceneProps) {
  const selectedPosition = MARKER_POSITIONS[selectedPointId] ?? MARKER_POSITIONS['FP-001']
  const selectedPoint = points.find((point) => point.id === selectedPointId) ?? null
  const floodPath = activeForecast === 'NOW'
    ? 'M298 520c33-42 70-58 111-52 32 5 54 26 85 22 29-4 54 14 71 42l-15 53-86 26-104-14-68-36Z'
    : activeForecast === 'PLUS_10'
      ? 'M250 498c46-52 94-74 148-65 45 8 71 34 107 27 48-9 87 17 109 54l-7 78-108 31-155-17-101-56Z'
      : 'M190 476c71-75 132-91 194-77 50 12 98 38 140 28 64-15 124 20 157 75l-5 106-139 43-188-22-144-72Z'

  return (
    <section className={`digital-twin-scene ${compact ? 'digital-twin-scene--compact' : ''}`} aria-label="上海数字孪生场景占位层">
      <div className="scene-atmosphere" />
      <svg className="scene-city" viewBox="0 0 1000 760" preserveAspectRatio="xMidYMid slice" role="img">
        <defs>
          <linearGradient id="sceneSky" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stopColor="#243c4b" /><stop offset="0.45" stopColor="#193341" /><stop offset="1" stopColor="#081a28" /></linearGradient>
          <linearGradient id="riverFill" x1="0" x2="1" y1="0" y2="1"><stop offset="0" stopColor="#244c5e" /><stop offset="0.5" stopColor="#0d4054" /><stop offset="1" stopColor="#092c42" /></linearGradient>
          <linearGradient id="floodFill" x1="0" x2="1" y1="0" y2="1"><stop offset="0" stopColor="#25d6e9" stopOpacity="0.85" /><stop offset="0.56" stopColor="#2b8dff" stopOpacity="0.72" /><stop offset="1" stopColor="#ff9a37" stopOpacity="0.82" /></linearGradient>
          <filter id="markerGlow" x="-100%" y="-100%" width="300%" height="300%"><feGaussianBlur stdDeviation="5" result="blur" /><feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge></filter>
        </defs>
        <rect width="1000" height="760" fill="url(#sceneSky)" />
        <path d="M0 112c122-51 237-34 347-1 130 40 246 35 346-5 98-39 193-43 307-3v93H0Z" fill="#78909b" opacity="0.18" />
        <path d="M0 188c129-36 217-38 340-3 142 41 243 31 356-7 111-37 197-38 304-2v60H0Z" fill="#b2c1c4" opacity="0.08" />
        <g className="scene-river" style={{ opacity: layers.water ? 1 : 0 }}>
          <path d="M673-40c-55 94-74 148-65 204 10 64 75 88 63 147-13 61-105 75-126 135-24 68 23 138 62 211l178 0c-39-85-86-155-70-225 13-59 79-76 90-137 13-75-58-108-51-170 6-47 51-94 98-165Z" fill="url(#riverFill)" />
          <path d="M674-16c-38 92-47 144-35 192 13 54 67 85 56 135-13 58-93 75-107 139-14 63 23 120 57 191" fill="none" stroke="#438da1" strokeOpacity="0.45" strokeWidth="4" />
          <path d="M709 18c-25 74-26 113-7 164 16 42 47 74 38 119-11 52-66 87-77 137-11 48 8 95 25 139" fill="none" stroke="#1f6b85" strokeOpacity="0.68" strokeWidth="2" strokeDasharray="10 14" />
        </g>
        <g className="scene-roads">
          <path d="M-40 629c197-105 310-138 477-120 139 15 272 62 608 13" fill="none" stroke="#6f8590" strokeOpacity="0.25" strokeWidth="22" />
          <path d="M-40 629c197-105 310-138 477-120 139 15 272 62 608 13" fill="none" stroke="#1b5368" strokeOpacity="0.9" strokeWidth="10" />
          <path d="M70 130c205 77 335 104 477 91 131-12 259-71 492-52" fill="none" stroke="#5e7c88" strokeOpacity="0.26" strokeWidth="18" />
          <path d="M70 130c205 77 335 104 477 91 131-12 259-71 492-52" fill="none" stroke="#1b5167" strokeOpacity="0.82" strokeWidth="8" />
          <path d="M240 760c47-137 89-250 135-360 45-107 72-197 75-380" fill="none" stroke="#224f62" strokeWidth="7" strokeOpacity="0.75" />
          <path d="M20 391c190-8 341 4 471 46 154 50 281 111 533 97" fill="none" stroke="#2b6074" strokeWidth="5" strokeOpacity="0.7" />
        </g>
        <g className="scene-buildings" style={{ opacity: layers.base ? 1 : 0 }}>
          {BUILDINGS.map(([x, y, width, height], index) => (
            <g key={`${x}-${y}`} opacity={0.48 + (index % 4) * 0.08}>
              <rect x={x} y={y} width={width} height={height} rx="2" fill={index % 3 === 0 ? '#365463' : '#2b4655'} />
              <path d={`M${x + width} ${y + 5}l${Math.round(width * 0.18)} -${Math.round(height * 0.08)}v${height}l-${Math.round(width * 0.18)} ${Math.round(height * 0.08)}Z`} fill="#172f3c" opacity="0.72" />
              <path d={`M${x + 5} ${y + 8}h${Math.max(width - 12, 8)}M${x + 5} ${y + 24}h${Math.max(width - 12, 8)}M${x + 5} ${y + 40}h${Math.max(width - 12, 8)}`} stroke="#86a1aa" strokeOpacity="0.12" strokeWidth="2" />
            </g>
          ))}
          <g className="scene-landmark" transform="translate(523 108)">
            <path d="M23 0h8l7 276H15Z" fill="#b4c3c5" opacity="0.82" />
            <path d="M21 58h12M20 119h14M18 187h18" stroke="#2d5969" strokeWidth="5" />
            <ellipse cx="27" cy="90" rx="38" ry="7" fill="#2f6172" opacity="0.7" />
            <ellipse cx="27" cy="155" rx="30" ry="6" fill="#2f6172" opacity="0.7" />
            <circle cx="27" cy="58" r="9" fill="#c3d0d2" />
          </g>
          <g className="scene-landmark scene-landmark--tower" transform="translate(625 167)">
            <path d="M30 0c-16 32-14 72 0 105 13-33 16-73 0-105Z" fill="#b2c3c8" opacity="0.78" />
            <path d="M30 98 9 268h42Z" fill="#728e99" opacity="0.48" />
            <circle cx="30" cy="78" r="22" fill="#d5d7d0" opacity="0.58" />
            <circle cx="30" cy="172" r="15" fill="#d5d7d0" opacity="0.48" />
          </g>
        </g>
        <g className="scene-network" style={{ opacity: layers.network ? 0.72 : 0 }}>
          <path d="M124 610c120-40 201-19 274 17 89 44 174 33 267-8 69-31 138-45 210-25" fill="none" stroke="#b86f4d" strokeWidth="2" strokeDasharray="4 8" />
          <path d="M300 295c71 29 113 68 156 125 33 42 87 71 160 79" fill="none" stroke="#b86f4d" strokeWidth="2" strokeDasharray="4 8" />
          <circle cx="594" cy="474" r="12" fill="none" stroke="#c77b52" strokeWidth="2" />
        </g>
        <g className="scene-flood-surface" style={{ opacity: layers.depth ? 1 : 0 }}>
          <path d={floodPath} fill="url(#floodFill)" opacity="0.34" stroke="#39d9ef" strokeWidth="3" strokeDasharray="8 6" />
          <path d={activeForecast === 'PLUS_30' ? 'M314 512c43-28 89-31 126-17 30 12 58 12 94-3' : 'M354 528c37-19 67-20 99-8 26 10 44 9 71-4'} fill="none" stroke="#b0f5ff" strokeOpacity="0.72" strokeWidth="3" />
        </g>
        <g className="scene-district-lines" opacity="0.18">
          <path d="M110 270c167 40 308 26 427-14M155 688c152-43 286-36 431 7M790 270c-62 69-70 154-23 231" fill="none" stroke="#a4c8d1" strokeWidth="1" strokeDasharray="3 9" />
        </g>
        {points.map((point) => {
          const position = MARKER_POSITIONS[point.id] ?? { x: 500, y: 400 }
          const selected = point.id === selectedPointId
          return (
            <g
              className={`scene-marker scene-marker--${point.riskLevel.toLowerCase()} ${selected ? 'is-selected' : ''}`}
              key={point.id}
              transform={`translate(${position.x} ${position.y})`}
              onClick={() => onPointSelect(point.id)}
              onKeyDown={(keyboardEvent) => {
                if (keyboardEvent.key === 'Enter' || keyboardEvent.key === ' ') onPointSelect(point.id)
              }}
              role="button"
              tabIndex={0}
              aria-label={`${point.name}，${RISK_LABEL[point.riskLevel]}`}
            >
              {selected && <circle r="23" className="marker-pulse" />}
              <path d="M0-16c-8 0-14 6-14 14 0 10 14 23 14 23S14 8 14-2C14-10 8-16 0-16Z" className="marker-pin" filter={selected ? 'url(#markerGlow)' : undefined} />
              <circle r="5" className="marker-core" />
              {selected && <text x="21" y="-13" className="marker-label">{point.depthCm.toFixed(1)} cm</text>}
            </g>
          )
        })}
        <g className="selected-popup" transform={`translate(${selectedPosition.x - 58} ${selectedPosition.y - 80})`}>
          <path d="M0 0h158a6 6 0 0 1 6 6v41a6 6 0 0 1-6 6H0Z" fill="#8c4c1d" fillOpacity="0.9" stroke="#f2a14b" strokeWidth="1" />
          <path d="m71 53 8 14 8-14" fill="#8c4c1d" stroke="#f2a14b" strokeWidth="1" />
          <text x="12" y="20" className="popup-title">{selectedPoint?.name ?? event?.name ?? '未关联点位'}</text>
          <text x="12" y="40" className="popup-value">{formatSceneDepth(event, selectedPoint, activeForecast, forecastFrame)} <tspan>cm</tspan></text>
        </g>
      </svg>
      <div className="scene-label scene-label--top"><span className="scene-status-dot" />SHANGHAI DIGITAL TWIN <small>SCENARIO DATA</small></div>
      <div className="scene-label scene-label--bottom">中心场景：{FORECAST_LABEL[activeForecast]} · {activeForecast === 'NOW' ? '当前积水范围' : '预测积水范围更新中'}</div>
      <div className="scene-toolbar-wrap"><LayerToolbar layers={layers} onToggle={onLayerToggle} /></div>
      <div className="scene-depth-legend"><DepthLegend /></div>
    </section>
  )
}

export function DigitalTwinScene({ event, points, activeForecast, forecastFrame = null, selectedPointId, layers, onPointSelect, onLayerToggle, compact = false }: DigitalTwinSceneProps) {
  const selectedPosition = MARKER_POSITIONS[selectedPointId] ?? MARKER_POSITIONS['FP-001']
  const selectedPoint = points.find((point) => point.id === selectedPointId) ?? null
  const floodPath = activeForecast === 'NOW'
    ? 'M430 530c28-25 70-31 105-19 31 10 46 25 64 44l-18 43-86 12-80-35Z'
    : activeForecast === 'PLUS_10'
      ? 'M350 500c48-38 110-47 158-22 46 24 84 32 111 72l-12 76-115 22-145-52Z'
      : 'M260 464c74-62 156-74 228-40 58 26 113 30 156 82l-4 102-141 42-199-55-84-81Z'

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
      <svg className="scene-overlay" viewBox="0 0 1000 760" preserveAspectRatio="xMidYMid slice" role="img" aria-label="风险点与积水 React overlay">
        <defs>
          <linearGradient id="overlayFloodFill" x1="0" x2="1" y1="0" y2="1"><stop offset="0" stopColor="#3de1ea" stopOpacity="0.55" /><stop offset="0.58" stopColor="#278bff" stopOpacity="0.42" /><stop offset="1" stopColor="#ff9a37" stopOpacity="0.66" /></linearGradient>
          <filter id="overlayMarkerGlow" x="-100%" y="-100%" width="300%" height="300%"><feGaussianBlur stdDeviation="4" result="blur" /><feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge></filter>
        </defs>
        <g className="scene-network" style={{ opacity: layers.network ? 0.64 : 0 }}>
          <path d="M124 610c120-40 201-19 274 17 89 44 174 33 267-8 69-31 138-45 210-25" fill="none" stroke="#d68a5a" strokeWidth="1.5" strokeDasharray="3 9" />
          <path d="M300 295c71 29 113 68 156 125 33 42 87 71 160 79" fill="none" stroke="#d68a5a" strokeWidth="1.5" strokeDasharray="3 9" />
        </g>
        <g className="scene-flood-surface" style={{ opacity: layers.depth ? 1 : 0 }}>
          <path d={floodPath} fill="url(#overlayFloodFill)" opacity="0.26" stroke="#55dfe8" strokeOpacity="0.72" strokeWidth="2" strokeDasharray="10 8" />
          <path d={activeForecast === 'PLUS_30' ? 'M314 512c43-28 89-31 126-17 30 12 58 12 94-3' : 'M354 528c37-19 67-20 99-8 26 10 44 9 71-4'} fill="none" stroke="#b8f3f1" strokeOpacity="0.54" strokeWidth="2" />
        </g>
        {points.map((point) => {
          const position = MARKER_POSITIONS[point.id] ?? { x: 500, y: 400 }
          const selected = point.id === selectedPointId
          return (
            <g
              className={`scene-marker scene-marker--${point.riskLevel.toLowerCase()} ${selected ? 'is-selected' : ''}`}
              key={point.id}
              transform={`translate(${position.x} ${position.y})`}
              onClick={() => onPointSelect(point.id)}
              onKeyDown={(keyboardEvent) => {
                if (keyboardEvent.key === 'Enter' || keyboardEvent.key === ' ') onPointSelect(point.id)
              }}
              role="button"
              tabIndex={0}
              aria-label={`${point.name}，${RISK_LABEL[point.riskLevel]}`}
            >
              {selected && <circle r="18" className="marker-pulse" />}
              {selected && <path d="M0-28V-8" className="marker-stem" filter="url(#overlayMarkerGlow)" />}
              <circle r={selected ? 5 : 3.5} className="marker-node" />
              {selected && <text x="14" y="-18" className="marker-label">{point.depthCm.toFixed(1)} cm</text>}
            </g>
          )
        })}
        <g className="selected-popup" transform={`translate(${selectedPosition.x - 63} ${selectedPosition.y - 47}) scale(0.74)`}>
          <path d="M0 0h172a6 6 0 0 1 6 6v39a6 6 0 0 1-6 6H0Z" fill="#653d24" fillOpacity="1" stroke="#e9a056" strokeWidth="1" />
          <path d="m77 50 8 13 8-13" fill="#653d24" stroke="#e9a056" strokeWidth="1" />
          <text x="10" y="18" className="popup-title">{selectedPoint?.name ?? event?.name ?? '未关联点位'}</text>
          <text x="10" y="36" className="popup-value">{formatSceneDepth(event, selectedPoint, activeForecast, forecastFrame)} <tspan>cm</tspan></text>
        </g>
      </svg>
      <div className="scene-label scene-label--top"><span className="scene-status-dot" />SHANGHAI DIGITAL TWIN <small>CESIUM CITY · L1</small></div>
      <div className="scene-label scene-label--bottom">中心场景：{FORECAST_LABEL[activeForecast]} · {activeForecast === 'NOW' ? '当前积水范围' : '预测积水范围更新中'}</div>
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
