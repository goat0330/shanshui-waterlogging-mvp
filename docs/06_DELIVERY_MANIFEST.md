# DELIVERY_MANIFEST
## 山水智鉴｜城市内涝智能防控中心 RC2 Evidence-Backed Demo

> 本清单只记录可复核的当前状态。`PASS` 只表示对应证据通过，不等于生产部署；`CONDITIONAL`、`NOT VERIFIED` 和 `VISUAL_REVIEW` 不得在演示中省略。

---

## 1. Candidate / canonical identity

```text
Status: CONDITIONAL / RC2.2 CANONICAL CLOSEOUT + VISUAL_REVIEW
Canonical branch: main
Current integrated functional checkpoint: d9f0661b0d24d535b4d28ad72441d17d28723ec2
RC2.2 Main repairs: 0349a6a (Cesium building emphasis) + 49d5673 (backend decision projection) + e2c9375 (Vision decision projection) + b6ea92a (dashboard decision surface) + 94735ac (waterlogging summary wiring) + 38df8df (video decision adapter)
Release tag: rc2-evidence-demo (immutable RC2 baseline; not moved)
Release tag target SHA: b0a41d1e2245e60ed55eef2777ea03d6b899d6c2
RC2.2 candidate tag: not created; Main is the review line
Public repository: https://github.com/goat0330/shanshui-waterlogging-mvp
Audit date: 2026-08-25
Viewport target: 1920x1080
```

The release is an evidence-backed demo, not a production system. Human visual acceptance remains the user's gate.

## 2. Entries and startup commands

| Item | Current entry / command |
|---|---|
| Frontend | `frontend/` — `npm install`, then `npm run dev` |
| Frontend typecheck/build | `npm run typecheck` and `npm run build` from `frontend/` |
| Frontend API mode | set `VITE_DATA_SOURCE=api` and `VITE_API_BASE_URL=http://127.0.0.1:8000` before `npm run dev` |
| Frontend fixture mode | leave `VITE_DATA_SOURCE` unset or use any value other than `api` |
| Backend | `backend/` — `python -m uvicorn app.main:app --reload --port 8000` |
| Backend smoke | `python -B smoke.py` from `backend/` |
| VisionDepth image API | `POST /api/v1/vision-depth/analyze/upload` and `POST /api/v1/vision-depth/analyze/url` |
| VisionDepth V2 video smoke | from `backend/visiondepth_v2/`: `python -m pytest -q`, `python -m tools.data_gate --config configs/local.yaml`, `python -m tools.video_smoke --config configs/local.yaml` |
| Cesium mount | `frontend/src/CesiumScene.tsx` through the main Dashboard; sensor/event/forecast/hydro layers are geographic seams |

## 3. Runtime modes and truth boundaries

| Domain | Current semantics |
|---|---|
| `SENSOR` | demo simulator/API telemetry evidence; current measured depth is kept separate from future forecast and vision observations |
| `VISION_IMAGE` | upload/URL observation through the guarded VisionDepth API; source, mask path, quality and provenance are retained |
| `VISION_VIDEO` | local-only V2 evidence adapter; sampled masks/JSON/overlay metadata; camera uncalibrated means no numeric centimetres |
| `FORECAST` | synthetic/demo NOW/+10/+30 GeoJSON and forecast values; NOW displays the sensor measured baseline and future frames do not overwrite it |
| City scene | OSM Buildings → local Core Local → explicit demo city-block fallback; current release does not claim official Shanghai Core Local availability |
| Hydrography | Huangpu GeoJSON is a stable synthetic demo seam, not official hydrography |

Local configuration values must not enter Git:

```text
VITE_CESIUM_ION_TOKEN
DATABASE_URL
REPOSITORY_BACKEND=postgres
```

## 4. Repository boundary

Do not stage `data/source/**`, `data/runtime/**`, `data/visiondepth/videos/**`, `*.mp4`, local Cesium runtime tiles, `node_modules/**`, `dist/**`, `.vite/`, `__pycache__/`, logs, `.env.local`, model weights, raw datasets or V2 runtime outputs. Public Git contains code, source metadata, instructions and safe documentation only.

The public source manifest is `docs/RC2_SOURCE_MANIFEST.csv`. The actual six-row runtime manifest and MP4 files live outside Git under the project-level `data/visiondepth/` root.

## 5. Gates

| Gate | Status | Evidence / exact limit |
|---|---|---|
| Main branch and source boundary | PASS | Main is the release line; release staging and runtime boundary audit passed |
| Backend memory Contract/Telemetry smoke | PASS | `python -B backend/smoke.py`; REST, CORS, WebSocket, telemetry, simulator, vision upload/URL and 404/422 boundaries |
| Shanghai public-source adapter | PASS / CONDITIONAL | `DATA_MODE=hybrid` live smoke returned 63 rainfall, 45 ponding and 55 water-level records; source remains provisional and does not alter the formal Contract |
| VisionDepth provenance contract | PASS | OpenAPI and JSON schema require `VISION_IMAGE`/`VISION_VIDEO` source provenance fields |
| Frontend TypeScript/build | PASS | `npm run typecheck`; `npm run build`; only the existing Cesium chunk warning |
| Dashboard decision integration | PASS / CONDITIONAL | API `waterloggingSituation` renders the summary block; image/video decision projection renders final Chinese product copy; user visual acceptance remains open |
| Contract semantic alignment | PASS | Frontend consumes `waterloggingSituation` directly; no second `summary` business field remains; frame-level `decision` is preserved through the video adapter |
| Generated runtime freshness | PASS / CONDITIONAL | V2 video smoke was regenerated from the current pipeline; ignored browser runtime overlay/masks were rebuilt, and the original FMP4 source was not modified |
| Cesium geographic demo path | PASS / CONDITIONAL | 1920×1080 browser smoke shows `OSM BUILDINGS · GLOBAL`, geographic FP-001 and forecast layers; local Core Local, official hydro and portable token deployment remain unverified |
| REST/WebSocket API mode | PASS | 1920×1080 browser smoke shows API summary and `API DATA · WS CONNECTED`; REST fallback/reconnect evidence remains from RC2.1 |
| 60-second core chain | PASS | `review/e2e/60-second-chain.json` |
| Five-minute rehearsal | PASS / CONDITIONAL | `review/e2e/5-minute-rehearsal.json`; 309.3s; CCTV/AI placeholder-conditional |
| Vision image | PASS / CONDITIONAL | 3-image OpenCV baseline and guarded upload/URL seam pass; generalization/production accuracy unverified |
| Vision image result delivery | PASS / CONDITIONAL | `flood_no_reference.jpg` API upload returns `decisionDepthCm=50`, `PROHIBITED`, mask artifact and final product card; the value is the lower bound of an open visual range, not calibrated sensor depth |
| MP4 → frame → evidence | PASS / CONDITIONAL | 4/6 videos pass `>=30` gate; 25 sampled frame JSON, masks, timestamps and overlay metadata; 2 source files have 11 frames |
| Video decision projection → Dashboard | PASS / CONDITIONAL | Current local runtime overlay renders `检测到积水 / 约 50 cm / 禁止通行`; raw decision enums remain in the adapter/technical evidence boundary |
| Browser image/video result surfaces | PASS / CONDITIONAL | API browser smoke verified image upload + mask + `约 50 cm / 禁止通行` and H.264 runtime video + the same frame decision; real production CCTV remains unverified |
| RC2.1 synthetic browser video | PASS / CONDITIONAL | `frontend/public/demo/video/flood_cam_017.mp4` decodes in Chrome; flat frame overlay normalizes to nearest timestamp; all depth cm remain null |
| RC2.1 SensorState → Cesium | PASS / CONDITIONAL | `SSZJ-NODE-001`, `28.6cm`, `WGS84 lon/lat`, `fallback=false` are passed to the geographic Cesium entity; official calibration remains unverified |
| RC2.1 provenance semantics | PASS | local upload=`not_required`; remote URL=`pending`; frontend provenance is required and rendered without `NOT ATTACHED` for controlled observations |
| Minimal GitHub Actions | ADDED / NOT VERIFIED | `.github/workflows/ci.yml` covers backend smoke, frontend typecheck/build and Vision smoke; remote run and branch protection are not independently verified |
| Camera calibration | NOT VERIFIED | all video `estimatedDepthCm=null`, `CAMERA_UNCALIBRATED` |
| Model upgrade | NOT VERIFIED | no authorized reproducible checkpoint, GT masks/depth labels or split; no model/accuracy claim |
| PostGIS | NOT VERIFIED | optional persistence path exists; live migration/spatial query/restart persistence not rerun in RC2 |
| Visual acceptance | VISUAL_REVIEW | screenshots are evidence only; final comparison belongs to user |
| Production / public redistribution | NOT VERIFIED | pending source license; `research_mvp=true`, `production=false`, `redistribution=false` |

## 6. Verified artifacts and known deviations

Verified commands on the integrated Main line:

- `python -B backend/smoke.py` — PASS, including VisionDepth upload provenance, URL SSRF boundary and SensorState non-overwrite.
- OpenAPI/JSON schema parity — PASS; both expose the same provenance fields.
- `python -m vision.smoke` — PASS for the three existing image evidence cases.
- From `backend/visiondepth_v2/`: `python -m pytest -q` — `7 passed`; `compileall` — PASS; `data_gate` — `4 usable videos`; `video_smoke` — PASS with `4 videos / 25 sampled frames / synthetic=false`; third-party check — `RESEARCH_MVP_LOCAL_ONLY`.
- Shanghai public-source hybrid smoke — PASS: `63` rainfall records, `45` ponding records and `55` water-level records; source coordinates remain explicitly `SOURCE_REPORTED_XX2000_YY2000`.
- `npm run typecheck` and `npm run build` — PASS.
- `node review/frontend/rc2.1-video-overlay-adapter-smoke.mjs` — PASS for flat-frame normalization, nearest timestamp selection and null-depth guard.
- Main browser smoke at `http://127.0.0.1:4173/` — PASS: 1920×1080 API mode renders the waterlogging summary, OSM Buildings scene label, geographic FP-001, WS-connected badge and the current video decision card; screenshot evidence is `review/e2e/rc22-main-1920x1080.jpg`.
- Main Vision browser smoke — PASS: local upload of `flood_no_reference.jpg` returns `检测到积水 / 约 50 cm / 禁止通行`, defaults to original-plus-mask AI result, and preserves technical details behind the collapsed section; screenshot evidence is `review/e2e/rc22-vision-api-1920x1080.jpg`.
- `review/e2e/api-realtime-browser-smoke.json` — PASS for API/WS/fallback/reconnect.
- `review/e2e/60-second-chain.json` — PASS for telemetry → event → Cesium → forecast → fallback → reconnect.
- `review/e2e/5-minute-rehearsal.json` — PASS for 309.3-second rehearsal and stable return.
- `review/e2e/vision-image-browser-smoke.json` — PASS for real API upload → VisionDepth observation → provenance rendering; event sensor depth remains `28.6cm`, page/console errors zero.
- Main post-release repair smoke — PASS for `flood_no_reference.jpg` → `floodDetected=true` → browser-readable PNG mask (`HTTP 200`, `image/png`); user-facing confidence field is removed, while the backend contract retains internal evidence fields.
- RC2.2 visual decision smoke — PASS for `flood_no_reference.jpg` → `estimatedDepthCm=null`, open range `[50,null]`, decision projection `decisionDepthCm=50.0` and `PROHIBITED`; the UI shows final product copy and does not expose level/range/confidence in the main card.
- Clean controlled Cesium smoke — PASS on an isolated fixture server; the historical fixed-port RC0 harness is not treated as a product failure because it observed a stale Vite process.

Known deviations:

- Fixture/demo values are not official Shanghai real-time or physical sensor data.
- Forecast GeoJSON and Huangpu geometry are synthetic/demo fixtures; they prove the integration seam only.
- OSM Buildings may require an environment token/network; local Core Local and formal building/control-point calibration are not verified.
- CCTV is a video evidence seam; the current browser asset is explicitly `SYNTHETIC_DEMO` and metadata-only, not a live city camera feed; no fake `LIVE` claim is made.
- V-FloodNet source metadata remains `licenseReview=pending`; MP4s and weights are not redistributed.
- Two official source MP4s genuinely contain 11 frames and are rejected by the 30-frame gate; no interpolation or duplicated frames are used.
- The four accepted videos are uncalibrated; the algorithm reports masks/levels/ranges and null numeric centimetres, not calibrated depth or accuracy.
- The research source MP4 is FMP4 and is kept unchanged under the external data root; the ignored browser runtime uses a derived H.264 Baseline copy so Chrome can decode the same verified frames.
- The current `50 cm` image/video decision is the lower bound of an open visual range and is used for the MVP action projection; it is not a physical calibration claim. The backend retains this distinction while the main UI presents the approved product decision copy.
- No labeled GT or approved checkpoint exists for a model-upgrade metric; `MODEL_UPGRADE=NOT_VERIFIED`.
- The first dashboard request for a known sensor before telemetry has a valid 404 (`sensor-state` absent). The API/5-minute smoke records this as an expected console 404; after telemetry the state is present and the chain passes.

## 7. Release checklist

- [x] Existing four workers reused; no new worker created for RC2.
- [x] Main independently reran backend, frontend, image, video, API, WS, Cesium controlled smoke and 60s/5m chains.
- [x] Source/provenance policy and scenarios documented.
- [x] Public source manifest and download boundary added without binaries.
- [x] Dashboard provenance narrow repair independently accepted.
- [x] RC2.1 synthetic video Overlay and SensorState → Cesium closure independently accepted on Main.
- [x] RC2.1 local upload/remote URL provenance semantics independently accepted.
- [x] RC2.2 backend waterlogging summary, unified decision projection and Dashboard API wiring accepted on Main.
- [x] RC2.2 local video frame decision adapter and 1920×1080 browser smoke accepted on Main.
- [x] Canonical field/runtime closeout: `waterloggingSituation`, frame-level `decision`, fresh runtime assets, and final browser image/video smoke.
- [x] Minimal CI workflow added; remote GitHub Actions execution remains unverified.
- [x] Final docs commit and explicit staged allowlist recorded.
- [x] GitHub `main` pushed.
- [x] `rc2-evidence-demo` tag created and pushed.
- [ ] User visual review completed.

## 8. Rollback

```text
RC0 rollback anchor: 78e96e7d4a85a4aa24368bbd0465002a0097e45b
RC1.1 historical checkpoint: 1430e56
RC2 pre-release integrated checkpoint: 5faa0bd
RC2.1 code checkpoint before closure docs: eb122f0
RC2.2 functional checkpoint: 38df8df
Recovery: use a commit-based revert after the RC2 tag exists; ignored runtime data is not part of Git rollback.
```
