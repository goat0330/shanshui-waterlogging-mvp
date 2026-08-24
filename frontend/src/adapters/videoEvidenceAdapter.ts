import type { VisionDepthObservation, VisionDepthProvenance } from '../types'

export type VideoEvidenceState = 'loading' | 'ready' | 'missing' | 'error'

export interface VideoEvidenceFrame {
  frameId: string
  timestampMs: number
  observation: VisionDepthObservation
  overlay?: {
    referenceBoxes?: unknown[]
  }
}

export interface VideoEvidenceBundle {
  frames: VideoEvidenceFrame[]
  synthetic: boolean
}

export interface VideoOverlayData {
  frameId: string
  timestampMs: number
  sourceType: VisionDepthProvenance['sourceType']
  sourceId: string
  runtimePolicy: VisionDepthProvenance['runtimePolicy']
  floodDetected: boolean
  level: number
  rangeCm: [number | null, number | null]
  estimatedDepthCm: number | null
  confidence: number
  method: VisionDepthObservation['method']
  quality: VisionDepthObservation['quality']
  qualityFlags: string[]
  synthetic: boolean
  objects?: Array<{
    type: 'vehicle' | 'person'
    left: number
    top: number
    width: number
    height: number
  }>
}

type RecordValue = Record<string, unknown>

function isRecord(value: unknown): value is RecordValue {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function hasProvenance(value: unknown): value is VisionDepthProvenance {
  if (!isRecord(value)) return false
  return (
    (value.sourceType === 'VISION_IMAGE' || value.sourceType === 'VISION_VIDEO') &&
    typeof value.sourceId === 'string' &&
    value.sourceId.length > 0 &&
    (value.observedAt === null || typeof value.observedAt === 'string') &&
    (value.licenseReview === 'approved' || value.licenseReview === 'pending' || value.licenseReview === 'not_required') &&
    (value.runtimePolicy === 'research_mvp' || value.runtimePolicy === 'production')
  )
}

function hasObservation(value: unknown): value is VisionDepthObservation {
  if (!isRecord(value) || !isRecord(value.source) || !isRecord(value.depth)) return false
  const rangeCm = value.depth.rangeCm
  return (
    typeof value.imageId === 'string' &&
    (value.source.type === 'local' || value.source.type === 'url') &&
    typeof value.source.value === 'string' &&
    hasProvenance(value.provenance) &&
    typeof value.floodDetected === 'boolean' &&
    typeof value.depth.level === 'number' &&
    (value.depth.estimatedDepthCm === null || typeof value.depth.estimatedDepthCm === 'number') &&
    Array.isArray(rangeCm) &&
    rangeCm.length === 2 &&
    (rangeCm[0] === null || typeof rangeCm[0] === 'number') &&
    (rangeCm[1] === null || typeof rangeCm[1] === 'number') &&
    typeof value.depth.confidence === 'number' &&
    typeof value.method === 'string' &&
    Array.isArray(value.referenceObjects) &&
    typeof value.waterMaskPath === 'string' &&
    typeof value.quality === 'string' &&
    Array.isArray(value.qualityFlags) &&
    isRecord(value.model) &&
    typeof value.synthetic === 'boolean'
  )
}

function normalizeFrame(value: unknown, index: number): VideoEvidenceFrame {
  if (!isRecord(value) || !hasObservation(value.observation)) {
    throw new Error(`Invalid video evidence frame at index ${index}`)
  }
  const timestampMs = typeof value.timestampMs === 'number' ? value.timestampMs : Number(value.timestampMs)
  if (!Number.isFinite(timestampMs) || timestampMs < 0) {
    throw new Error(`Invalid video evidence timestamp at index ${index}`)
  }
  const frameId = typeof value.frameId === 'string' && value.frameId.length > 0 ? value.frameId : value.observation.imageId
  const overlay = isRecord(value.overlay)
    ? { referenceBoxes: Array.isArray(value.overlay.referenceBoxes) ? value.overlay.referenceBoxes : undefined }
    : undefined
  return { frameId, timestampMs, observation: value.observation, overlay }
}

export function parseVideoEvidenceBundle(value: unknown): VideoEvidenceBundle {
  if (!isRecord(value) || !Array.isArray(value.frames) || value.frames.length === 0) {
    throw new Error('Video evidence bundle has no frames')
  }
  const frames = value.frames.map(normalizeFrame).sort((left, right) => left.timestampMs - right.timestampMs)
  return {
    frames,
    synthetic: value.synthetic === true || frames.every((frame) => frame.observation.synthetic),
  }
}

export async function loadVideoEvidence(url: string): Promise<VideoEvidenceBundle> {
  if (!url) throw new Error('Video evidence overlay URL is missing')
  const response = await fetch(url, { headers: { Accept: 'application/json' } })
  if (!response.ok) throw new Error(`Video evidence ${response.status} ${url}`)
  return parseVideoEvidenceBundle(await response.json())
}

export function selectNearestVideoFrame(bundle: VideoEvidenceBundle, currentTimeSec: number): VideoEvidenceFrame | null {
  if (bundle.frames.length === 0 || !Number.isFinite(currentTimeSec)) return null
  const targetMs = Math.max(0, currentTimeSec * 1000)
  return bundle.frames.reduce((nearest, frame) => {
    const nearestDistance = Math.abs(nearest.timestampMs - targetMs)
    const frameDistance = Math.abs(frame.timestampMs - targetMs)
    return frameDistance < nearestDistance ? frame : nearest
  })
}

function readPercent(value: unknown): number | null {
  return typeof value === 'number' && value >= 0 && value <= 100 ? value : null
}

function normalizeReferenceBoxes(value: unknown[] | undefined): VideoOverlayData['objects'] {
  if (!value) return undefined
  const objects = value.flatMap((item) => {
    if (!isRecord(item)) return []
    const type = item.type === 'vehicle' || item.type === 'person' ? item.type : null
    const left = readPercent(item.left)
    const top = readPercent(item.top)
    const width = readPercent(item.width)
    const height = readPercent(item.height)
    return type && left !== null && top !== null && width !== null && height !== null
      ? [{ type: type as 'vehicle' | 'person', left, top, width, height }]
      : []
  })
  return objects.length > 0 ? objects : undefined
}

export function toVideoOverlayData(frame: VideoEvidenceFrame): VideoOverlayData {
  const observation = frame.observation
  return {
    frameId: frame.frameId,
    timestampMs: frame.timestampMs,
    sourceType: observation.provenance.sourceType,
    sourceId: observation.provenance.sourceId,
    runtimePolicy: observation.provenance.runtimePolicy,
    floodDetected: observation.floodDetected,
    level: observation.depth.level,
    rangeCm: observation.depth.rangeCm,
    estimatedDepthCm: observation.depth.estimatedDepthCm,
    confidence: observation.depth.confidence,
    method: observation.method,
    quality: observation.quality,
    qualityFlags: observation.qualityFlags,
    synthetic: observation.synthetic,
    objects: normalizeReferenceBoxes(frame.overlay?.referenceBoxes),
  }
}
