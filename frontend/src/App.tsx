import { useEffect, useState } from 'react'
import { getForecastSurfaceAdapter } from './adapters/forecastSurfaceAdapter'
import {
  loadVideoEvidence,
  selectNearestVideoFrame,
  toVideoOverlayData,
  type VideoEvidenceBundle,
  type VideoEvidenceState,
} from './adapters/videoEvidenceAdapter'
import {
  AIAnalysisPanel,
  AppShell,
  CctvCard,
  DigitalTwinScene,
  EventPanel,
  ForecastPreview,
  RankingPanel,
  RainfallPanel,
  SensorEvidence,
  StatusPanel,
  TimelineBar,
  TopNav,
  VisionDepthDrawer,
  type LayerVisibility,
} from './components'
import { homeFixtures } from './data/homeFixtures'
import { useDashboardData } from './hooks/useDashboardData'
import { useRealtimeTelemetry } from './hooks/useRealtimeTelemetry'
import { useSelectedEventCoordinator } from './hooks/useSelectedEventCoordinator'
import { DATA_SOURCE } from './services/apiClient'
import { analyzeVisionDepthUpload, analyzeVisionDepthUrl } from './services/visionDepthClient'
import type { Camera, DashboardData, FloodEvent, ForecastKey, RainfallSnapshot, SensorState, VisionDepthObservation } from './types'
import './styles.css'

const DEFAULT_LAYERS: LayerVisibility = {
  base: true,
  water: true,
  depth: true,
  network: false,
  video: true,
  measure: false,
}

const heavyRainFixture: RainfallSnapshot = {
  ...homeFixtures.rainfall,
  intensityMmH: 92,
  trend: homeFixtures.rainfall.trend.map((item, index) => ({
    ...item,
    valueMmH: Math.min(98, item.valueMmH + index * 4),
  })),
}

const criticalEventFixture: FloodEvent = {
  ...homeFixtures.event,
  riskLevel: 'CRITICAL',
  currentDepthCm: 48.8,
  pipeLoadPercent: 97,
}

const offlineCamera: Camera = {
  ...homeFixtures.camera,
  status: 'OFFLINE',
}

function createDemoSensorEvidence(event: FloodEvent): SensorState {
  return {
    sensorId: 'SSZJ-NODE-001',
    siteId: 'SITE-RML-BJDD',
    coordinates: event.coordinates,
    depthMm: event.currentDepthCm * 10,
    depthCm: event.currentDepthCm,
    waterDetected: event.currentDepthCm > 0,
    observedAt: event.startedAt,
    receivedAt: homeFixtures.overview.updatedAt,
    transport: 'SIMULATOR',
    source: 'DEMO_DEVICE',
  }
}

const DEMO_VISION_OBSERVATION: VisionDepthObservation = {
  imageId: 'DEMO-VISION-DEPTH',
  source: { type: 'local', value: 'DEMO_FIXTURE' },
  provenance: {
    sourceType: 'VISION_IMAGE',
    sourceId: 'DEMO-VISION-DEPTH',
    observedAt: null,
    licenseReview: 'not_required',
    runtimePolicy: 'research_mvp',
  },
  floodDetected: true,
  depth: {
    level: 0,
    estimatedDepthCm: null,
    rangeCm: [null, null],
    confidence: 0,
  },
  method: 'NO_REFERENCE',
  referenceObjects: [],
  waterMaskPath: 'DEMO_FIXTURE_MASK_NOT_ATTACHED',
  quality: 'REJECT',
  qualityFlags: ['DEMO_FIXTURE', 'NO_REFERENCE'],
  model: { waterSegmentation: 'fixture-only' },
  synthetic: true,
}

export default function App() {
  const isGallery = window.location.pathname.replace(/\/+$/, '') === '/gallery'
  return isGallery ? <GalleryPage /> : <DashboardPage />
}

interface DashboardFrameProps {
  data: DashboardData
  initialForecast?: ForecastKey
  statusVariant?: 'default' | 'high-risk'
  eventOverride?: FloodEvent
  fixedPreview?: boolean
  dataBadge?: string
}

function DashboardFrame({ data, initialForecast = 'NOW', statusVariant = 'default', eventOverride, fixedPreview = false, dataBadge = 'DEMO SCENARIO DATA · FIXTURE' }: DashboardFrameProps) {
  const [activeForecast, setActiveForecast] = useState<ForecastKey>(initialForecast)
  const [selectedPointId, setSelectedPointId] = useState('FP-001')
  const [layers, setLayers] = useState<LayerVisibility>(DEFAULT_LAYERS)
  const [visionOpen, setVisionOpen] = useState(false)
  const [visionMode, setVisionMode] = useState<'local' | 'url'>('local')
  const [visionSourceValue, setVisionSourceValue] = useState('')
  const [visionFile, setVisionFile] = useState<File | null>(null)
  const [visionPreviewUrl, setVisionPreviewUrl] = useState<string | null>(null)
  const [visionState, setVisionState] = useState<'idle' | 'loading' | 'error' | 'ready'>('idle')
  const [visionError, setVisionError] = useState<string | null>(null)
  const [visionObservation, setVisionObservation] = useState<VisionDepthObservation | null>(null)
  const [videoEvidence, setVideoEvidence] = useState<VideoEvidenceBundle | null>(null)
  const [videoEvidenceState, setVideoEvidenceState] = useState<VideoEvidenceState>('missing')
  const [videoReady, setVideoReady] = useState(false)
  const [videoTimeSec, setVideoTimeSec] = useState(0)
  const selectedEvent = useSelectedEventCoordinator({
    selectedPointId,
    points: data.points,
    event: eventOverride ?? data.event,
    forecast: data.forecast,
    analysis: data.analysis,
    camera: data.camera,
  })
  const forecastSurface = getForecastSurfaceAdapter(selectedEvent.forecast, activeForecast)
  const sensor = data.sensor ?? (dataBadge.includes('FIXTURE') && selectedEvent.event ? createDemoSensorEvidence(selectedEvent.event) : null)
  const forecastSourceLabel = dataBadge.includes('API DATA') ? 'ADAPTER · SYNTHETIC' : 'SYNTHETIC FIXTURE'
  const cameraId = selectedEvent.camera?.id ?? null
  const overlayUrl = selectedEvent.camera?.overlayUrl ?? null

  useEffect(() => {
    if (!visionFile) {
      setVisionPreviewUrl(null)
      return
    }
    const nextUrl = URL.createObjectURL(visionFile)
    setVisionPreviewUrl(nextUrl)
    return () => URL.revokeObjectURL(nextUrl)
  }, [visionFile])

  useEffect(() => {
    setVideoEvidence(null)
    setVideoReady(false)
    setVideoTimeSec(0)
    if (!overlayUrl) {
      setVideoEvidenceState('missing')
      return
    }

    let cancelled = false
    setVideoEvidenceState('loading')
    loadVideoEvidence(overlayUrl)
      .then((bundle) => {
        if (cancelled) return
        setVideoEvidence(bundle)
        setVideoEvidenceState('ready')
      })
      .catch(() => {
        if (cancelled) return
        setVideoEvidenceState('error')
      })

    return () => {
      cancelled = true
    }
  }, [cameraId, overlayUrl])

  const toggleLayer = (layer: keyof LayerVisibility) => {
    setLayers((current) => ({ ...current, [layer]: !current[layer] }))
  }

  const selectVisionFile = (file: File | null) => {
    setVisionFile(file)
    setVisionSourceValue(file?.name ?? '')
    setVisionObservation(null)
    setVisionError(null)
    setVisionState('idle')
  }

  const analyzeVision = async () => {
    if (visionMode === 'local' && !visionFile) {
      setVisionError('请先选择本地图片')
      setVisionState('error')
      return
    }
    if (visionMode === 'url' && !visionSourceValue.trim()) {
      setVisionError('请先输入图片 URL')
      setVisionState('error')
      return
    }

    setVisionState('loading')
    setVisionError(null)
    try {
      const observation = DATA_SOURCE === 'api'
        ? visionMode === 'local'
          ? await analyzeVisionDepthUpload(visionFile as File)
          : await analyzeVisionDepthUrl(visionSourceValue.trim())
        : {
            ...DEMO_VISION_OBSERVATION,
            source: { type: visionMode, value: visionMode === 'local' ? visionFile?.name ?? 'DEMO_FIXTURE' : visionSourceValue.trim() },
          }
      setVisionObservation(observation)
      setVisionState('ready')
    } catch (reason: unknown) {
      setVisionError(reason instanceof Error ? reason.message : String(reason))
      setVisionState('error')
    }
  }

  const selectedVideoFrame = videoReady && videoEvidence ? selectNearestVideoFrame(videoEvidence, videoTimeSec) : null
  const videoOverlayData = selectedVideoFrame ? toVideoOverlayData(selectedVideoFrame) : undefined

  return (
    <div className={`dashboard-frame ${fixedPreview ? 'dashboard-frame--fixed-preview' : ''}`}>
      <DigitalTwinScene
        event={selectedEvent.event}
        points={data.points}
        activeForecast={activeForecast}
        forecastFrame={forecastSurface.frame}
        selectedPointId={selectedPointId}
        layers={layers}
        onPointSelect={setSelectedPointId}
        onLayerToggle={toggleLayer}
      />
      <TopNav overview={data.overview} updatedAt={data.timeline.currentTime} />
      <div className="dashboard-side dashboard-side--left">
        <StatusPanel overview={data.overview} variant={statusVariant} />
        <RainfallPanel rainfall={data.rainfall} stationName={data.rainfallRanking[0]?.stationName} />
        <RankingPanel ranking={data.rainfallRanking} />
      </div>
      <div className="dashboard-side dashboard-side--right">
        <EventPanel event={selectedEvent.event} analysis={selectedEvent.analysis} sensor={sensor} onOpenVision={() => setVisionOpen(true)} />
        <ForecastPreview forecast={selectedEvent.forecast} activeKey={activeForecast} measuredDepthCm={sensor?.depthCm ?? null} sourceLabel={forecastSourceLabel} onChange={setActiveForecast} />
        <CctvCard
          camera={selectedEvent.camera}
          showOverlay={layers.video}
          overlayData={videoOverlayData}
          videoEvidenceState={videoEvidenceState}
          onVideoReady={setVideoReady}
          onVideoTimeUpdate={setVideoTimeSec}
        />
      </div>
      <TimelineBar timeline={data.timeline} activeKey={activeForecast} onForecastChange={setActiveForecast} />
      <div className="dashboard-demo-badge">{dataBadge}</div>
      <VisionDepthDrawer
        open={visionOpen}
        mode={visionMode}
        sourceValue={visionSourceValue}
        sourcePreviewUrl={visionPreviewUrl}
        fileName={visionFile?.name}
        state={visionState}
        errorMessage={visionError}
        observation={visionObservation}
        onClose={() => setVisionOpen(false)}
        onModeChange={(mode) => {
          setVisionMode(mode)
          setVisionObservation(null)
          setVisionError(null)
          setVisionState('idle')
        }}
        onSourceChange={(value) => {
          setVisionSourceValue(value)
          setVisionObservation(null)
          setVisionError(null)
          setVisionState('idle')
        }}
        onFileChange={selectVisionFile}
        onAnalyze={analyzeVision}
      />
    </div>
  )
}

function DashboardPage() {
  const state = new URLSearchParams(window.location.search).get('state')
  const initialForecast: ForecastKey = state === 'plus30' ? 'PLUS_30' : 'NOW'
  const highRisk = state === 'high-risk' || state === 'plus30'
  const dashboard = useDashboardData()
  const realtime = useRealtimeTelemetry({
    enabled: dashboard.source === 'api',
    onSensorUpdated: dashboard.applySensorState,
    onRestFallback: dashboard.reload,
  })
  const data = dashboard.data ?? homeFixtures
  const dataBadge = dashboard.source === 'api'
    ? dashboard.error ? 'API UNAVAILABLE · FIXTURE FALLBACK' : `API DATA · WS ${realtime.status.toUpperCase()}`
    : 'DEMO SCENARIO DATA · FIXTURE'

  return (
    <AppShell className="dashboard-app">
      <DashboardFrame data={data} initialForecast={initialForecast} statusVariant={highRisk ? 'high-risk' : 'default'} eventOverride={state === 'high-risk' ? criticalEventFixture : undefined} dataBadge={dataBadge} />
    </AppShell>
  )
}

function GalleryPage() {
  return (
    <AppShell className="gallery-app">
      <TopNav overview={homeFixtures.overview} updatedAt={homeFixtures.timeline.currentTime} />
      <div className="gallery-page">
        <section className="gallery-hero">
          <div>
            <p className="eyebrow">FRONTEND MVP · COMPONENT GALLERY</p>
            <h1>首页组件预览</h1>
            <p>真实 React 组件、Contract fixture Mock 与关键状态。这里用于人工视觉 review，不代表完整业务系统。</p>
          </div>
          <a className="back-to-dashboard" href="/">返回实时监测 <span>↗</span></a>
        </section>

        <div className="gallery-state-strip">
          <span><i className="state-dot state-dot--implemented" />IMPLEMENTED：组件结构与状态已接入</span>
          <span><i className="state-dot state-dot--review" />VISUAL_REVIEW：等待用户对照目标图与 Golden</span>
          <span className="gallery-viewport-note">目标视口 1920 × 1080</span>
        </div>

        <section className="gallery-section">
          <GallerySectionTitle title="Layout / Core Panels" note="页面骨架与核心业务面板" />
          <div className="gallery-grid gallery-grid--panels">
            <GalleryCard title="StatusPanel" stateName="default">
              <StatusPanel overview={homeFixtures.overview} />
            </GalleryCard>
            <GalleryCard title="StatusPanel" stateName="high-risk">
              <StatusPanel overview={homeFixtures.overview} variant="high-risk" />
            </GalleryCard>
            <GalleryCard title="StatusPanel" stateName="empty">
              <StatusPanel overview={homeFixtures.overview} state="empty" />
            </GalleryCard>
            <GalleryCard title="RainfallPanel" stateName="default">
              <RainfallPanel rainfall={homeFixtures.rainfall} />
            </GalleryCard>
            <GalleryCard title="RainfallPanel" stateName="heavy-rain">
              <RainfallPanel rainfall={heavyRainFixture} />
            </GalleryCard>
            <GalleryCard title="RainfallPanel" stateName="loading">
              <RainfallPanel rainfall={homeFixtures.rainfall} state="loading" />
            </GalleryCard>
            <GalleryCard title="RainfallPanel" stateName="empty">
              <RainfallPanel rainfall={homeFixtures.rainfall} state="empty" />
            </GalleryCard>
            <GalleryCard title="RankingPanel" stateName="default">
              <RankingPanel ranking={homeFixtures.rainfallRanking} />
            </GalleryCard>
            <GalleryCard title="RankingPanel" stateName="empty">
              <RankingPanel ranking={[]} state="empty" />
            </GalleryCard>
          </div>
        </section>

        <section className="gallery-section">
          <GallerySectionTitle title="Selected Event / Forecast / CCTV" note="风险、预测控制器与现场证据状态" />
          <div className="gallery-grid gallery-grid--panels">
            <GalleryCard title="EventPanel" stateName="selected / high-risk">
              <EventPanel event={homeFixtures.event} analysis={homeFixtures.analysis} sensor={createDemoSensorEvidence(homeFixtures.event)} />
            </GalleryCard>
            <GalleryCard title="EventPanel" stateName="critical">
              <EventPanel event={criticalEventFixture} analysis={homeFixtures.analysis} sensor={createDemoSensorEvidence(criticalEventFixture)} />
            </GalleryCard>
            <GalleryCard title="EventPanel" stateName="loading">
              <EventPanel event={homeFixtures.event} analysis={homeFixtures.analysis} state="loading" />
            </GalleryCard>
            <GalleryCard title="EventPanel" stateName="empty">
              <EventPanel event={homeFixtures.event} analysis={homeFixtures.analysis} state="empty" />
            </GalleryCard>
            <GalleryCard title="ForecastPreview" stateName="NOW active">
              <ForecastPreview forecast={homeFixtures.forecast} activeKey="NOW" measuredDepthCm={createDemoSensorEvidence(homeFixtures.event).depthCm} onChange={() => undefined} />
            </GalleryCard>
            <GalleryCard title="ForecastPreview" stateName="+30 active">
              <ForecastPreview forecast={homeFixtures.forecast} activeKey="PLUS_30" measuredDepthCm={createDemoSensorEvidence(homeFixtures.event).depthCm} onChange={() => undefined} />
            </GalleryCard>
            <GalleryCard title="ForecastPreview" stateName="loading">
              <ForecastPreview forecast={homeFixtures.forecast} activeKey="NOW" onChange={() => undefined} state="loading" />
            </GalleryCard>
            <GalleryCard title="ForecastPreview" stateName="empty">
              <ForecastPreview forecast={homeFixtures.forecast} activeKey="NOW" onChange={() => undefined} state="empty" />
            </GalleryCard>
            <GalleryCard title="CctvCard" stateName="media seam + overlay">
              <CctvCard camera={homeFixtures.camera} />
            </GalleryCard>
            <GalleryCard title="CctvCard" stateName="offline">
              <CctvCard camera={offlineCamera} />
            </GalleryCard>
            <GalleryCard title="CctvCard" stateName="loading">
              <CctvCard camera={homeFixtures.camera} state="loading" />
            </GalleryCard>
            <GalleryCard title="CctvCard" stateName="empty">
              <CctvCard camera={homeFixtures.camera} state="empty" />
            </GalleryCard>
            <GalleryCard title="SensorEvidence" stateName="DEMO_DEVICE / stale fixture">
              <SensorEvidence sensor={createDemoSensorEvidence(homeFixtures.event)} />
            </GalleryCard>
            <GalleryCard title="VisionDepthDrawer" stateName="local upload / contract empty">
              <VisionDepthGalleryPreview />
            </GalleryCard>
          </div>
        </section>

        <section className="gallery-section">
            <GallerySectionTitle title="Scene / Timeline / AI" note="未来 Cesium mount point、全局时间与研判展示" />
          <div className="gallery-grid gallery-grid--wide-components">
            <GalleryCard title="DigitalTwinScene" stateName="NOW / selected event" className="gallery-card--scene">
              <div className="gallery-scene-preview gallery-scene-only"><SceneOnlyPreview /></div>
            </GalleryCard>
            <GalleryCard title="TimelineBar" stateName="realtime">
              <TimelineBar timeline={homeFixtures.timeline} activeKey="NOW" onForecastChange={() => undefined} />
            </GalleryCard>
            <GalleryCard title="TimelineBar" stateName="playback">
              <TimelineBar timeline={{ ...homeFixtures.timeline, mode: 'PLAYBACK' }} activeKey="NOW" onForecastChange={() => undefined} />
            </GalleryCard>
            <GalleryCard title="TimelineBar" stateName="forecast +30">
              <TimelineBar timeline={{ ...homeFixtures.timeline, mode: 'FORECAST' }} activeKey="PLUS_30" onForecastChange={() => undefined} />
            </GalleryCard>
            <GalleryCard title="AIAnalysisPanel" stateName="expanded">
              <AIAnalysisPanel analysis={homeFixtures.analysis} expanded />
            </GalleryCard>
          </div>
        </section>

        <section className="gallery-section">
          <GallerySectionTitle title="Full Dashboard States" note="同一套真实组件的组合状态，不是截图" />
          <div className="gallery-review-links" aria-label="全屏 Dashboard review 入口">
            <a href="/?state=default">打开 Default 全屏 ↗</a>
            <a href="/?state=high-risk">打开 High Risk 全屏 ↗</a>
            <a href="/?state=plus30">打开 Forecast +30 全屏 ↗</a>
          </div>
          <div className="full-dashboard-gallery">
            <DashboardStateCard label="A · Default" note="城市态势 default · NOW · selected event · demo video" initialForecast="NOW" statusVariant="default" />
            <DashboardStateCard label="B · High Risk" note="风险色增强但不铺满页面 · selected event" initialForecast="NOW" statusVariant="high-risk" event={criticalEventFixture} />
            <DashboardStateCard label="C · Forecast +30" note="中央场景、预测摘要与 Timeline 同步到 PLUS_30" initialForecast="PLUS_30" statusVariant="high-risk" event={homeFixtures.event} />
          </div>
        </section>

        <footer className="gallery-footer">状态：<strong>IMPLEMENTED</strong> / <strong>VISUAL_REVIEW</strong> · 等待用户进行视觉 Review · 不代表 Cesium、后端或真实视频已验证</footer>
      </div>
    </AppShell>
  )
}

function VisionDepthGalleryPreview() {
  const [open, setOpen] = useState(false)
  const [mode, setMode] = useState<'local' | 'url'>('local')
  const [sourceValue, setSourceValue] = useState('')
  const [fileName, setFileName] = useState<string>()
  const [state, setState] = useState<'idle' | 'loading' | 'error' | 'ready'>('idle')
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [observation, setObservation] = useState<VisionDepthObservation | null>(null)

  const showState = (nextState: 'idle' | 'loading' | 'error' | 'ready') => {
    setOpen(true)
    setState(nextState)
    setErrorMessage(nextState === 'error' ? 'Gallery error state · API unavailable' : null)
    setObservation(nextState === 'ready' ? { ...DEMO_VISION_OBSERVATION, source: { type: mode, value: sourceValue || 'DEMO_FIXTURE' } } : null)
  }

  return (
    <div className="gallery-vision-preview">
      <p>同页入口：local upload / direct URL；状态由真实 Drawer 展示。</p>
      <div className="gallery-vision-actions">
        <button type="button" onClick={() => showState('idle')}>empty</button>
        <button type="button" onClick={() => showState('loading')}>loading</button>
        <button type="button" onClick={() => showState('error')}>error</button>
        <button type="button" onClick={() => showState('ready')}>ready</button>
      </div>
      <VisionDepthDrawer
        open={open}
        mode={mode}
        sourceValue={sourceValue}
        fileName={fileName}
        state={state}
        errorMessage={errorMessage}
        observation={observation}
        onClose={() => setOpen(false)}
        onModeChange={setMode}
        onSourceChange={setSourceValue}
        onFileChange={(file) => {
          setFileName(file?.name)
          setSourceValue(file?.name ?? '')
        }}
        onAnalyze={() => showState('ready')}
      />
    </div>
  )
}

function SceneOnlyPreview() {
  const [selectedPointId, setSelectedPointId] = useState('FP-001')
  const [layers, setLayers] = useState<LayerVisibility>(DEFAULT_LAYERS)

  return (
    <DigitalTwinScene
      event={homeFixtures.event}
      points={homeFixtures.points}
      activeForecast="NOW"
      forecastFrame={getForecastSurfaceAdapter(homeFixtures.forecast, 'NOW').frame}
      selectedPointId={selectedPointId}
      layers={layers}
      onPointSelect={setSelectedPointId}
      onLayerToggle={(layer) => setLayers((current) => ({ ...current, [layer]: !current[layer] }))}
      compact
    />
  )
}

interface GalleryCardProps {
  title: string
  stateName: string
  children: React.ReactNode
  className?: string
}

function GalleryCard({ title, stateName, children, className = '' }: GalleryCardProps) {
  return (
    <article className={`gallery-card ${className}`.trim()}>
      <header className="gallery-card-header"><strong>{title}</strong><span>{stateName}</span></header>
      <div className="gallery-card-body">{children}</div>
    </article>
  )
}

function GallerySectionTitle({ title, note }: { title: string; note: string }) {
  return <div className="gallery-section-title"><h2>{title}</h2><span>{note}</span></div>
}

interface DashboardStateCardProps {
  label: string
  note: string
  initialForecast: ForecastKey
  statusVariant: 'default' | 'high-risk'
  event?: FloodEvent
}

function DashboardStateCard({ label, note, initialForecast, statusVariant, event }: DashboardStateCardProps) {
  return (
    <article className="dashboard-state-card">
      <header><strong>{label}</strong><span>{note}</span></header>
      <div className="dashboard-state-viewport"><DashboardFrame data={homeFixtures} initialForecast={initialForecast} statusVariant={statusVariant} eventOverride={event} fixedPreview /></div>
    </article>
  )
}
