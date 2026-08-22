# RC2 Main Progress

## Define Goal

`RC2 — EVIDENCE-BACKED DEMO RELEASE`

收口一条可以正式录制 5 分钟演示的视频主线：

```text
Sensor measured depth
+ Vision image/video evidence
+ Forecast
+ Cesium geographic scene
+ Dashboard source truth
```

每个数值必须能区分 `SENSOR`、`VISION_IMAGE`、`VISION_VIDEO`、`FORECAST`，并保留 confidence、quality、synthetic、licenseReview 和 runtime policy。视觉结果不得覆盖传感器实测值。

## Canonical state

```text
Public repository: https://github.com/goat0330/shanshui-waterlogging-mvp
RC2 integrated code checkpoint: 5faa0bd
Canonical branch: main
Viewport target: 1920x1080
Current decision: CONDITIONAL / RC2 + VISUAL_REVIEW
```

`5faa0bd` 是当前已独立回归的代码检查点（含 Dashboard provenance 窄修复）；最终 release commit 由 `rc2-evidence-demo` tag 指向，并在发布后回写本文件。

Runtime video evidence remains outside Git:

```text
data/visiondepth/manifests/video_manifest.csv
data/visiondepth/videos/*.mp4
```

6 个 manifest entries 中 4 个通过 `>=30` 帧 gate；2 个官方源文件真实只有 11 帧，保持 rejected，不插帧、不复制帧、不修改原文件。视频相机未标定，因此逐帧结果保持 `estimatedDepthCm=null` 和 `CAMERA_UNCALIBRATED`。

## Worker ownership and accepted checkpoints

| Worker | Existing thread | Accepted checkpoint | Main state | Evidence boundary |
|---|---|---|---|---|
| Cesium | `01a022d3-0777-7742-907d-85ee96bc2bed` | worker `7988220`; Main merge `d43387d` | ACCEPTED / CONDITIONAL | Geographic sensor/event/forecast layers pass; real Shanghai Core Local, official hydrography and portable OSM access remain unverified |
| Backend | `01a02258-3560-7f73-8187-771c41a8968e` | worker `a7b41e4`; Main merges `6958726`, `9629766` | ACCEPTED | Upload/URL safety and provenance pass; memory backend is the verified runtime, PostGIS remains unverified |
| Dashboard | `01a02258-9e68-74f3-b2c7-914477e82389` | worker `2693a65`; Main merge `72159e2` | ACCEPTED / VISUAL_REVIEW | Source separation, forecast semantics and vision drawer are implemented; final human visual acceptance remains open |
| Vision/Video | `01a02504-912d-7b40-98c0-6247eed72720` | worker `78c5383`; Main merge `7ebb829` | CONDITIONAL | 4-video/25-frame local smoke passes; license is pending, 2 files fail frame gate, model upgrade and calibrated centimetres are not verified |

Main is the only integration and release line. No new worker was created in RC2.

## Accepted product surfaces

- Backend: `POST /api/v1/vision-depth/analyze/upload` and `/url`; URL scheme, redirect, MIME, size and private-target guards; provenance is returned with the observation; SensorState/FloodPoint are not overwritten.
- Dashboard: `SENSOR`, `VISION_IMAGE`, `VISION_VIDEO`, and `FORECAST` are separate source domains. `NOW` renders the measured sensor baseline; `+10/+30` render forecast frames. CCTV remains an explicit media seam/placeholder when no legal local media is attached.
- Cesium: city source order is OSM Buildings → local Core Local → explicit demo city-block fallback. Huangpu river, sensors, FP-001/event and NOW/+10/+30 are geographic entities/GeoJSON, not screen-space business coordinates.
- VisionDepth V2: MP4 → sampled frames → mask → timestamped observation JSON → overlay metadata. Uncalibrated camera depth is null by design.

## Independent Main evidence

| Check | Result | Evidence |
|---|---|---|
| Backend regression | PASS | `python -B backend/smoke.py` — REST, WebSocket, telemetry, forecast, analysis, upload, URL boundary and non-overwrite checks |
| Contract parity | PASS | OpenAPI and `contracts/schemas/vision-depth-observation.schema.json` both require matching `provenance` fields |
| Frontend typecheck/build | PASS | `npm run typecheck`; `npm run build`; only the existing Cesium large-chunk warning remains |
| Vision image smoke | PASS | `python -m vision.smoke` — 3 existing image evidence cases |
| Vision video smoke | PASS / CONDITIONAL | `5 passed`; data gate `4 usable videos`; video smoke `4 videos / 25 sampled frames / synthetic=false`; all uncalibrated depths null |
| API browser chain | PASS | `review/e2e/api-realtime-browser-smoke.json` — API mode, live WS, REST fallback and reconnect |
| 60-second chain | PASS | `review/e2e/60-second-chain.json` — telemetry → event → geographic forecast → fallback → reconnect; page errors zero |
| 5-minute rehearsal | PASS / CONDITIONAL | `review/e2e/5-minute-rehearsal.json` — 309.3s, Sensor → FP-001 → 12cm/28.6cm → +10/+30 → NOW → CCTV/AI conditional → stable return |
| Vision image browser chain | PASS / CONDITIONAL | `review/e2e/vision-image-browser-smoke.json` — upload → observation/provenance UI; event Sensor remains 28.6cm; video/calibrated cm remain conditional |
| Cesium controlled smoke | PASS / CONDITIONAL | clean fixture server on an isolated port: no page/console errors, hydro ready, forecast switch, orbit/zoom; old RC0 harness is conditional because it hardcodes port 5173 and observed a stale Vite process |
| Source manifest audit | PASS | 6 rows with source URL, project, SHA-256 and runtime policy; binaries remain outside Git |

The two generic `404` entries in the API/5-minute browser evidence are the expected initial `GET /api/v1/sensors/SSZJ-NODE-001` before the first telemetry observation creates state. Backend smoke explicitly preserves this distinction: known sensor without a latest state returns 404; after telemetry it returns 200. It is not a failed product chain and must not be hidden as a fake initial state.

## Open conditional gates

1. `licenseReview=pending` for the V-FloodNet research source; local research MVP is allowed, production and redistribution are not.
2. Two source MP4s contain only 11 frames; no 6/6 claim is made.
3. No authorized reproducible segmentation checkpoint, GT mask/depth labels or split is present; `MODEL_UPGRADE=NOT_VERIFIED`.
4. Camera calibration is absent; no calibrated centimetre depth or accuracy metric is claimed.
5. Shanghai Core Local tileset/SHP/SKP calibration and official Huangpu hydrography are not verified in this release; demo/OSM fallback is explicitly labeled.
6. CCTV is not a live feed; the UI uses `MEDIA / PLACEHOLDER` when no legal local media is attached.
7. Final visual acceptance is `VISUAL_REVIEW` and belongs to the user.

## RC2 finalization sequence

```text
Dashboard provenance narrow repair
→ update acceptance / delivery / source docs
→ independent regression and source-boundary audit
→ commit Main
→ push main
→ tag rc2-evidence-demo
→ push tag
→ final user visual review
```

No new model, dependency, page, contract field, or city-data claim is admitted after feature freeze.
