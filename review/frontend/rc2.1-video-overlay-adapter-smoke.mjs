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

const frame = (frameId, timestampMs) => ({
  frameId,
  timestampMs,
  observation: {
    imageId: frameId,
    source: { type: 'local', value: 'SYNTHETIC_DEMO' },
    provenance: {
      sourceType: 'VISION_VIDEO',
      sourceId: 'CAM-017',
      observedAt: null,
      licenseReview: 'not_required',
      runtimePolicy: 'research_mvp',
    },
    floodDetected: true,
    depth: { level: 2, estimatedDepthCm: null, rangeCm: [10, 30], confidence: 0.4 },
    method: 'NO_REFERENCE',
    referenceObjects: [],
    waterMaskPath: 'SYNTHETIC_DEMO_MASK',
    quality: 'LOW',
    qualityFlags: ['SYNTHETIC_DEMO', 'CAMERA_UNCALIBRATED'],
    model: {},
    synthetic: true,
  },
})

const bundle = module.exports.parseVideoEvidenceBundle({
  synthetic: true,
  frames: [frame('FRAME-0000', 0), frame('FRAME-0500', 500)],
})
const selected = module.exports.selectNearestVideoFrame(bundle, 0.42)
if (selected?.frameId !== 'FRAME-0500') throw new Error('nearest timestamp selection failed')

const overlay = module.exports.toVideoOverlayData(selected)
if (overlay.estimatedDepthCm !== null || Object.hasOwn(overlay, 'waterDepthCm')) {
  throw new Error('video adapter fabricated calibrated water depth')
}
if (!overlay.synthetic || !overlay.qualityFlags.includes('CAMERA_UNCALIBRATED')) {
  throw new Error('video provenance labels were lost')
}

console.log('PASS — timestamp nearest-frame mapping and null-depth provenance')
