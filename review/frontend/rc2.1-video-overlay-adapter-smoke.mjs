import { readFileSync } from 'node:fs'
import { createRequire } from 'node:module'

const require = createRequire(new URL('../../frontend/package.json', import.meta.url))
const typescript = require('typescript')
const source = readFileSync(new URL('../../frontend/src/adapters/videoEvidenceAdapter.ts', import.meta.url), 'utf8')
const output = typescript.transpileModule(source, {
  compilerOptions: { module: typescript.ModuleKind.CommonJS, target: typescript.ScriptTarget.ES2022 },
}).outputText
const module = { exports: {} }
new Function('module', 'exports', output)(module, module.exports)

const frame = (frameIndex, timestampMs) => ({
  frameIndex,
  timestampMs,
  floodDetected: true,
  level: 2,
  rangeCm: [10, 30],
  estimatedDepthCm: null,
  confidence: 0.4,
  method: 'NO_REFERENCE',
  quality: 'LOW',
  qualityFlags: ['SYNTHETIC_DEMO', 'CAMERA_UNCALIBRATED'],
  waterMaskPath: 'SYNTHETIC_DEMO_MASK',
  referenceObjects: [],
  referenceBoxes: [],
  overlay: { status: 'METADATA_ONLY', rendered: false, referenceBoxes: [] },
})

const bundle = module.exports.parseVideoEvidenceBundle({
  videoId: 'CAM-017',
  source: { type: 'local', value: '/demo/video/flood_cam_017.mp4', mediaType: 'video/mp4' },
  provenance: {
    sourceType: 'VISION_VIDEO',
    sourceId: 'CAM-017',
    observedAt: null,
    licenseReview: 'not_required',
    runtimePolicy: 'research_mvp',
  },
  synthetic: true,
  model: { framePipeline: 'synthetic-demo' },
  frames: [frame(0, 0), frame(1, 500)],
})
const selected = module.exports.selectNearestVideoFrame(bundle, 0.42)
if (selected?.frameId !== 'CAM-017-F000001') throw new Error('flat nearest timestamp selection failed')
if (selected?.observation.provenance.sourceType !== 'VISION_VIDEO') throw new Error('flat provenance normalization failed')

const overlay = module.exports.toVideoOverlayData(selected)
if (overlay.estimatedDepthCm !== null || Object.hasOwn(overlay, 'waterDepthCm')) {
  throw new Error('video adapter fabricated calibrated water depth')
}
if (!overlay.synthetic || !overlay.qualityFlags.includes('CAMERA_UNCALIBRATED')) {
  throw new Error('video provenance labels were lost')
}

console.log('PASS — timestamp nearest-frame mapping and null-depth provenance')
