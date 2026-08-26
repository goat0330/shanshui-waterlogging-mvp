import type { CSSProperties } from 'react'
import type { SceneAnchorPosition } from './CesiumScene'
import type { AIAnalysis, FloodEvent, HistoricalFloodCase, SensorState } from './types'

const RISK_LABEL: Record<FloodEvent['riskLevel'], string> = {
  NORMAL: '正常',
  WARNING: '警戒',
  HIGH: '高风险',
  CRITICAL: '严重',
}

const CARD_WIDTH = 252
const LIVE_CARD_HEIGHT = 316
const HISTORY_CARD_HEIGHT = 270
const LEFT_SAFE = 392
const RIGHT_SAFE = 404
const TOP_SAFE = 102
const BOTTOM_SAFE = 104
const ANCHOR_GAP = 16

function clamp(value: number, minimum: number, maximum: number) {
  return Math.min(Math.max(value, minimum), Math.max(minimum, maximum))
}

function cardStyle(anchor: SceneAnchorPosition, historical: boolean): CSSProperties {
  const cardHeight = historical ? HISTORY_CARD_HEIGHT : LIVE_CARD_HEIGHT
  const maxLeft = anchor.viewportWidth - RIGHT_SAFE - CARD_WIDTH
  let left = anchor.x + ANCHOR_GAP
  if (left + CARD_WIDTH > anchor.viewportWidth - RIGHT_SAFE) {
    left = anchor.x - CARD_WIDTH - ANCHOR_GAP
  }
  left = clamp(left, LEFT_SAFE, maxLeft)
  const top = clamp(anchor.y - 76, TOP_SAFE, anchor.viewportHeight - BOTTOM_SAFE - cardHeight)
  return { left: Math.round(left), top: Math.round(top) }
}

function formatEventName(value: string) {
  return value.replace(/\s*[×xX]\s*/g, ' · ')
}

function formatClock(value: string) {
  return new Intl.DateTimeFormat('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  }).format(new Date(value))
}

interface SceneEventOverlayProps {
  open: boolean
  anchor: SceneAnchorPosition | null
  event: FloodEvent | null
  historicalCase?: HistoricalFloodCase | null
  analysis?: AIAnalysis | null
  sensor?: SensorState | null
  sensorId?: string | null
  onClose: () => void
}

export function SceneEventOverlay({
  open,
  anchor,
  event,
  historicalCase = null,
  analysis = null,
  sensor = null,
  sensorId = null,
  onClose,
}: SceneEventOverlayProps) {
  if (!open || !anchor?.visible || (!event && !historicalCase)) return null
  const style = cardStyle(anchor, Boolean(historicalCase))

  if (historicalCase) {
    const depth = historicalCase.depthCm != null
      ? `${historicalCase.depthCm.toFixed(1)} cm`
      : historicalCase.depthEvidenceText ?? '来源未说明'
    return (
      <article className="scene-event-card scene-event-card--historical" style={style} aria-label="历史内涝事件详情">
        <header className="scene-event-card-header">
          <div>
            <span className="scene-event-card-kicker">历史内涝事件</span>
            <h3>{historicalCase.locationText}</h3>
          </div>
          <div className="scene-event-card-head-actions">
            <span className="scene-event-card-history-badge">历史</span>
            <button type="button" className="scene-event-card-close" aria-label="关闭事件卡片" onClick={onClose}>×</button>
          </div>
        </header>
        <section className="scene-event-card-section scene-event-card-section--facts">
          <div className="scene-event-card-row"><span>位置</span><strong>{historicalCase.district}</strong></div>
          <div className="scene-event-card-row"><span>事件日期</span><strong>{historicalCase.incidentDate}</strong></div>
          <div className="scene-event-card-row"><span>来源水深</span><strong className="scene-event-card-value--warning">{depth}</strong></div>
        </section>
        <section className="scene-event-card-section">
          <h4>交通影响</h4>
          <p className="scene-event-card-copy">{historicalCase.trafficImpact ?? '官方来源未逐项说明交通影响'}</p>
        </section>
        <section className="scene-event-card-section scene-event-card-section--actions">
          <h4>官方处置</h4>
          <div className="scene-event-card-actions">
            {historicalCase.officialActions.slice(0, 3).map((action, index) => (
              <span className={`scene-event-card-action scene-event-card-action--${index + 1}`} key={action}>{action}</span>
            ))}
            {historicalCase.officialActions.length === 0 && <span className="scene-event-card-empty">来源未逐项说明</span>}
          </div>
        </section>
      </article>
    )
  }

  if (!event) return null
  const currentDepthCm = sensor?.depthCm ?? event.currentDepthCm
  const actions = analysis?.actions.slice().sort((left, right) => left.priority - right.priority).slice(0, 3) ?? []
  return (
    <article className={`scene-event-card scene-event-card--${event.riskLevel.toLowerCase()}`} style={style} aria-label="选中积水事件详情">
      <header className="scene-event-card-header">
        <div>
          <span className="scene-event-card-kicker">内涝事件</span>
          <h3>{formatEventName(event.name)}</h3>
        </div>
        <div className="scene-event-card-head-actions">
          <span className={`scene-event-card-risk scene-event-card-risk--${event.riskLevel.toLowerCase()}`}>{RISK_LABEL[event.riskLevel]}</span>
          <button type="button" className="scene-event-card-close" aria-label="关闭事件卡片" onClick={onClose}>×</button>
        </div>
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
          <span className={`scene-event-card-sensor-status ${sensor ? 'scene-event-card-sensor-status--online' : 'scene-event-card-sensor-status--no_evidence'}`}>{sensor ? '已上报' : '未上报'}</span>
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
