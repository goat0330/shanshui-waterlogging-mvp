# DELIVERY_MANIFEST
## 山水智鉴｜城市内涝智能防控中心 RC2 Evidence-Backed Demo

> 本清单只记录可复核的当前状态。`PASS` 只表示对应证据通过，不等于生产部署；`CONDITIONAL`、`NOT VERIFIED` 和 `VISUAL_REVIEW` 不得在演示中省略。

---

## 1. Candidate / canonical identity

```text
Status: CONDITIONAL / RC2 + VISUAL_REVIEW
Canonical branch: main
Integrated code checkpoint before release docs: 5faa0bd
Release tag: rc2-evidence-demo (points to the final release commit)
Public repository: https://github.com/goat0330/shanshui-waterlogging-mvp
Audit date: 2026-08-23
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
| Main branch and source boundary | PASS / pending final tag | Main is the release line; final staged allowlist and tag audit are still required before publication |
| Backend memory Contract/Telemetry smoke | PASS | `python -B backend/smoke.py`; REST, CORS, WebSocket, telemetry, simulator, vision upload/URL and 404/422 boundaries |
| VisionDepth provenance contract | PASS | OpenAPI and JSON schema require `VISION_IMAGE`/`VISION_VIDEO` source provenance fields |
| Frontend TypeScript/build | PASS | `npm run typecheck`; `npm run build`; only the existing Cesium chunk warning |
| Cesium geographic demo path | PASS / CONDITIONAL | geographic sensors/event/forecast/hydro smoke passes; Core Local, official hydro and portable OSM deployment remain unverified |
| REST/WebSocket API mode | PASS | browser evidence covers live WS, REST fallback polling and reconnect; initial known-sensor/no-state 404 is expected |
| 60-second core chain | PASS | `review/e2e/60-second-chain.json` |
| Five-minute rehearsal | PASS / CONDITIONAL | `review/e2e/5-minute-rehearsal.json`; 309.3s; CCTV/AI placeholder-conditional |
| Vision image | PASS / CONDITIONAL | 3-image OpenCV baseline and guarded upload/URL seam pass; generalization/production accuracy unverified |
| MP4 → frame → evidence | PASS / CONDITIONAL | 4/6 videos pass `>=30` gate; 25 sampled frame JSON, masks, timestamps and overlay metadata; 2 source files have 11 frames |
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
- From `backend/visiondepth_v2/`: `python -m pytest -q` — `5 passed`; `compileall` — PASS; `data_gate` — `4 usable videos`; `video_smoke` — PASS with `4 videos / 25 sampled frames / synthetic=false`; third-party check — `RESEARCH_MVP_LOCAL_ONLY`.
- `npm run typecheck` and `npm run build` — PASS.
- `review/e2e/api-realtime-browser-smoke.json` — PASS for API/WS/fallback/reconnect.
- `review/e2e/60-second-chain.json` — PASS for telemetry → event → Cesium → forecast → fallback → reconnect.
- `review/e2e/5-minute-rehearsal.json` — PASS for 309.3-second rehearsal and stable return.
- `review/e2e/vision-image-browser-smoke.json` — PASS for real API upload → VisionDepth observation → provenance rendering; event sensor depth remains `28.6cm`, page/console errors zero.
- Clean controlled Cesium smoke — PASS on an isolated fixture server; the historical fixed-port RC0 harness is not treated as a product failure because it observed a stale Vite process.

Known deviations:

- Fixture/demo values are not official Shanghai real-time or physical sensor data.
- Forecast GeoJSON and Huangpu geometry are synthetic/demo fixtures; they prove the integration seam only.
- OSM Buildings may require an environment token/network; local Core Local and formal building/control-point calibration are not verified.
- CCTV is a video evidence seam, not a live city camera feed; no fake `LIVE` claim is made.
- V-FloodNet source metadata remains `licenseReview=pending`; MP4s and weights are not redistributed.
- Two official source MP4s genuinely contain 11 frames and are rejected by the 30-frame gate; no interpolation or duplicated frames are used.
- The four accepted videos are uncalibrated; the algorithm reports masks/levels/ranges and null numeric centimetres, not calibrated depth or accuracy.
- No labeled GT or approved checkpoint exists for a model-upgrade metric; `MODEL_UPGRADE=NOT_VERIFIED`.
- The first dashboard request for a known sensor before telemetry has a valid 404 (`sensor-state` absent). The API/5-minute smoke records this as an expected console 404; after telemetry the state is present and the chain passes.

## 7. Release checklist

- [x] Existing four workers reused; no new worker created for RC2.
- [x] Main independently reran backend, frontend, image, video, API, WS, Cesium controlled smoke and 60s/5m chains.
- [x] Source/provenance policy and scenarios documented.
- [x] Public source manifest and download boundary added without binaries.
- [x] Dashboard provenance narrow repair independently accepted.
- [ ] Final docs commit and explicit staged allowlist recorded.
- [ ] GitHub `main` pushed.
- [ ] `rc2-evidence-demo` tag created and pushed.
- [ ] User visual review completed.

## 8. Rollback

```text
RC0 rollback anchor: 78e96e7d4a85a4aa24368bbd0465002a0097e45b
RC1.1 historical checkpoint: 1430e56
RC2 pre-release integrated checkpoint: 5faa0bd
Recovery: use a commit-based revert after the RC2 tag exists; ignored runtime data is not part of Git rollback.
```
