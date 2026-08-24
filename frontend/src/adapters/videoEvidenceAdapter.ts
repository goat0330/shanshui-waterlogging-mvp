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

const VISION_METHODS: VisionDepthObservation['method'][] = [
  'VISUAL_RANGE',
  'NO_REFERENCE',
  'PERSON_REFERENCE',
  'VEHICLE_REFERENCE',
  'TRAFFIC_SIGN_REFERENCE',
  'FIXED_CAMERA_REFERENCE',
]

const VISION_QUALITIES: VisionDepthObservation['quality'][] = ['LOW', 'MEDIUM', 'HIGH', 'REJECT']

function isRecord(value: unknown): value is RecordValue {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
}

function isFiniteNumber(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value)
}

function isNullableFiniteNumber(value: unknown): value is number | null {
  return value === null || isFiniteNumber(value)
}

function isRangeCm(value: unknown): value is [number | null, number | null] {
  return Array.isArray(value) && value.length === 2 && value.every(isNullableFiniteNumber)
}

function isVisionMethod(value: unknown): value is VisionDepthObservation['method'] {
  return typeof value === 'string' && VISION_METHODS.includes(value as VisionDepthObservation['method'])
}

function isVisionQuality(value: unknown): value is VisionDepthObservation['quality'] {
  return typeof value === 'string' && VISION_QUALITIES.includes(value as VisionDepthObservation['quality'])
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
  return (
    typeof value.imageId === 'string' &&
    value.imageId.length > 0 &&
    (value.source.type === 'local' || value.source.type === 'url') &&
    typeof value.source.value === 'string' &&
    hasProvenance(value.provenance) &&
    typeof value.floodDetected === 'boolean' &&
    isFiniteNumber(value.depth.level) &&
    isNullableFiniteNumber(value.depth.estimatedDepthCm) &&
    isRangeCm(value.depth.rangeCm) &&
    isFiniteNumber(value.depth.confidence) &&
    isVisionMethod(value.method) &&
    Array.isArray(value.referenceObjects) &&
    value.referenceObjects.every(isRecord) &&
    typeof value.waterMaskPath === 'string' &&
    isVisionQuality(value.quality) &&
    Array.isArray(value.qualityFlags) &&
    value.qualityFlags.every((flag) => typeof flag === 'string') &&
    isRecord(value.model) &&
    typeof value.synthetic === 'boolean'
  )
}

function readSource(frame: RecordValue, bundle: RecordValue): { type: 'local' | 'url'; value: string } | null {
  const candidate = isRecord(frame.source) ? frame.source : isRecord(bundle.source) ? bundle.source : null
  if (!candidate || (candidate.type !== 'local' && candidate.type !== 'url') || typeof candidate.value !== 'string') return null
  return { type: candidate.type, value: candidate.value }
}

function readProvenance(frame: RecordValue, bundle: RecordValue): VisionDepthProvenance | null {
  if (hasProvenance(frame.provenance)) return frame.provenance
  if (hasProvenance(bundle.provenance)) return bundle.provenance
  return null
}

function normalizeFlatObservation(frame: RecordValue, bundle: RecordValue, index: number): VisionDepthObservation {
  const source = readSource(frame, bundle)
  const provenance = readProvenance(frame, bundle)
  const rangeCm = frame.rangeCm
  const qualityFlags = frame.qualityFlags
  const referenceObjects = frame.referenceObjects
  const model = isRecord(frame.model) ? frame.model : isRecord(bundle.model) ? bundle.model : {}
  const synthetic = typeof frame.synthetic === 'boolean' ? frame.synthetic : bundle.synthetic
  const videoId = typeof bundle.videoId === 'string' && bundle.videoId.length > 0 ? bundle.videoId : provenance?.sourceId
  const frameIndex = isFiniteNumber(frame.frameIndex) ? frame.frameIndex : index
  const suppliedFrameId = typeof frame.frameId === 'string' && frame.frameId.length > 0 ? frame.frameId : null
  const imageId = suppliedFrameId ?? `${videoId ?? provenance?.sourceId ?? 'VIDEO'}-F${String(frameIndex).padStart(6, '0')}`

  if (
    !source ||
    !provenance ||
    typeof frame.floodDetected !== 'boolean' ||
    !isFiniteNumber(frame.level) ||
    !isNullableFiniteNumber(frame.estimatedDepthCm) ||
    !isRangeCm(rangeCm) ||
    !isFiniteNumber(frame.confidence) ||
    !isVisionMethod(frame.method) ||
    !isVisionQuality(frame.quality) ||
    !Array.isArray(qualityFlags) ||
    !qualityFlags.every((flag) => typeof flag === 'string') ||
    !Array.isArray(referenceObjects) ||
    !referenceObjects.every(isRecord) ||
    typeof frame.waterMaskPath !== 'string' ||
    typeof synthetic !== 'boolean'
  ) {
    throw new Error(`Invalid flat video evidence frame at index ${index}`)
  }

  return {
    imageId,
    source,
    provenance,
    floodDetected: frame.floodDetected,
    depth: {
      level: frame.level,
      estimatedDepthCm: frame.estimatedDepthCm,
      rangeCm,
      confidence: frame.confidence,
    },
    method: frame.method,
    referenceObjects,
    waterMaskPath: frame.waterMaskPath,
    quality: frame.quality,
    qualityFlags,
    model,
    synthetic,
  }
}

function normalizeFrame(value: unknown, index: number, bundle: RecordValue): VideoEvidenceFrame {
  if (!isRecord(value)) throw new Error(`Invalid video evidence frame at index ${index}`)
  const observation = hasObservation(value.observation) ? value.observation : normalizeFlatObservation(value, bundle, index)
  const timestampMs = typeof value.timestampMs === 'number' ? value.timestampMs : Number(value.timestampMs)
  if (!Number.isFinite(timestampMs) || timestampMs < 0) {
    throw new Error(`Invalid video evidence timestamp at index ${index}`)
  }
  const frameId = typeof value.frameId === 'string' && value.frameId.length > 0 ? value.frameId : observation.imageId
  const referenceBoxes = isRecord(value.overlay) && Array.isArray(value.overlay.referenceBoxes)
    ? value.overlay.referenceBoxes
    : Array.isArray(value.referenceBoxes) ? value.referenceBoxes : undefined
  const overlay = referenceBoxes ? { referenceBoxes } : undefined
  return { frameId, timestampMs, observation, overlay }
}

export function parseVideoEvidenceBundle(value: unknown): VideoEvidenceBundle {
  if (!isRecord(value) || !Array.isArray(value.frames) || value.frames.length === 0) {
    throw new Error('Video evidence bundle has no frames')
  }
  const frames = value.frames.map((frame, index) => normalizeFrame(frame, index, value)).sort((left, right) => left.timestampMs - right.timestampMs)
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
