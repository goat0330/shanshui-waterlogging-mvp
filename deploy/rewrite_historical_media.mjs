#!/usr/bin/env node

import fs from 'node:fs'
import path from 'node:path'

const [dataPathArg, mediaRootArg] = process.argv.slice(2)
if (!dataPathArg || !mediaRootArg) {
  console.error('usage: node rewrite_historical_media.mjs <historical-cases.json> <media-root>')
  process.exit(2)
}

const dataPath = path.resolve(dataPathArg)
const mediaRoot = path.resolve(mediaRootArg)
const payload = JSON.parse(fs.readFileSync(dataPath, 'utf8'))

let rewritten = 0

for (const record of payload.records ?? []) {
  if (!record?.candidateId || record?.media?.sourceType !== 'CASE_SOURCE_MEDIA') continue

  const caseDir = path.join(mediaRoot, 'historical', record.candidateId)
  if (!fs.existsSync(caseDir) || !fs.statSync(caseDir).isDirectory()) continue

  const files = fs.readdirSync(caseDir)
    .filter((name) => /\.(png|jpe?g|webp)$/i.test(name))
    .sort()

  if (!files.length) continue

  record.media.urls = files.map(
    (name) => `/media/historical/${encodeURIComponent(record.candidateId)}/${encodeURIComponent(name)}`,
  )
  rewritten += 1
}

if (rewritten > 0) {
  fs.writeFileSync(dataPath, `${JSON.stringify(payload, null, 2)}\n`, 'utf8')
}

console.log(`RC2.4 historical media localization: ${rewritten} case(s) rewritten`)
