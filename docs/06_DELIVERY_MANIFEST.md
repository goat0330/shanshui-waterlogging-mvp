# DELIVERY_MANIFEST
## 山水智鉴｜城市内涝智能防控中心 MVP RC1.1

> 本清单只记录可复核的当前状态。`PASS` 仅表示对应证据通过，不等于生产部署；`CONDITIONAL` 和 `NOT VERIFIED` 不得在演示中省略。

---

## 1. Candidate / canonical identity

```text
Status: PASS — RC1.1 TECHNICAL / VISUAL_REVIEW
Canonical branch: main (observed)
Canonical source commit: 8c3e582 (RC1.1 + VisionDepth V2 guarded scaffold)
Audit date: 2026-08-23
Viewport target: 1920×1080
Release decision: RC1.1 technical path canonicalized; VisionDepth V2 remains conditional; human visual review and production assets remain open
```

RC0 rollback anchor: `78e96e7d4a85a4aa24368bbd0465002a0097e45b`. The RC1.1 source integration commit is `57d2a9f`.

## 2. Entries and startup commands

| Item | Current entry / command |
|---|---|
| Frontend | `frontend/` — `npm install`, `npm run typecheck`, `npm run dev` |
| Frontend build | `npm run build` from `frontend/` — `PASS` on the integrated tree; generated `dist/` remains ignored |
| Backend | `backend/` — `python -m pip install -r requirements.txt`, then `python -m uvicorn app.main:app --reload --port 8000` |
| Backend smoke | `python -B smoke.py` from `backend/` |
| Cesium mount | `frontend/src/CesiumScene.tsx` through the main frontend; geographic hydro/sensor/forecast seams are integrated |
| Legacy Cesium PoC | `spikes/cesium/` — evidence/spike only, not the canonical frontend entry |
| Integration boundary | `integration/` — adapter/mode documentation; no independent runtime entry |

## 3. Runtime modes and environment names

Values are local configuration only and must never enter Git.

| Name | Required when | Current semantics |
|---|---|---|
| `VITE_DATA_SOURCE` | API mode | `api` selects REST/WebSocket; any other/unset value uses fixture mode |
| `VITE_API_BASE_URL` | API mode, if overriding local default | Backend base URL; code default is local `127.0.0.1:8000` |
| `VITE_CESIUM_ION_TOKEN` | OSM Buildings path | Optional for local Huangpu fallback; required only for separately verified OSM access |
| `REPOSITORY_BACKEND` | PostgreSQL path | Unset/default is in-memory `FixtureRepository`; `postgres` selects the optional persistence path |
| `DATABASE_URL` | `REPOSITORY_BACKEND=postgres` | Database connection name only; no value is committed |
| `SMOKE_PORT` | Smoke port override | Optional backend smoke port; default is the script default |

The current RC0 code does not read an LLM API key. CCTV has no required media-server credential because the current view is a marked placeholder.

## 4. Repository boundary

Do not stage `data/source/**`, `data/runtime/**`, local Cesium runtime tiles, either `node_modules/**` tree, `dist/**`, `.vite/`, `__pycache__/`, logs, `.env.local`, `.codex/**`, or `frontend/review/*.zip`. `.gitignore` covers the runtime/secret classes and RC0 now explicitly ignores the two local/generated classes. Keep only the small `spikes/cesium/public/data/tiles/shanghai-aoi/manifest.json` exception when the parent intentionally stages it.

## 5. Gates

| Gate | Status | Evidence / exact limit |
|---|---|---|
| Repository root, branch, ignore boundary | PASS | Root is `git/`; branch is `main`; secret scan emitted no values; canonical commit recorded below |
| Backend memory Contract/Telemetry smoke | PASS | `python -B backend/smoke.py`; REST, CORS, WebSocket, telemetry projection, simulator, 404/422 boundaries passed |
| Frontend TypeScript | PASS | `npm run typecheck` in `frontend/` |
| Frontend production build | PASS | `npm run typecheck` and `npm run build`; only the existing Cesium large-chunk warning remains |
| Main local Cesium/Huangpu fallback | PASS (demo technical path) | Cesium geographic smoke/evidence; local runtime tiles remain outside Git and the real Core Local tileset is unavailable |
| OSM Buildings | CONDITIONAL | OSM/demo path is retained; portable token/network/deployment status is not verified in RC1.1 |
| REST/WebSocket frontend API mode | PASS / CONDITIONAL | `review/e2e/api-realtime-browser-smoke.json`; live, REST fallback polling, and reconnect passed; forced outage logs are expected |
| Cesium geographic FP-001 marker | PASS (technical/demo) | WGS84 demo point is loaded as a Cesium geographic entity; formal survey/building calibration remains open |
| Cesium geographic NOW/+10/+30 surface | PASS (technical/demo) | Synthetic GeoJSON surfaces switched and rendered ready in the 60-second browser chain |
| WS → REST fallback | PASS / CONDITIONAL | 5s polling observed after WS failure and stopped after reconnect; induced network errors are expected evidence |
| CCTV/video | CONDITIONAL | Real `<video>` seam and explicit `DEMO / PLACEHOLDER` fallback exist; no legal MP4/RTSP/CCTV feed is present |
| VisionDepth | CONDITIONAL | OpenCV baseline, three-image evidence, upload/URL API seam and UI drawer pass; production accuracy, calibrated centimetres and generalization are `NOT VERIFIED` |
| MP4 → frame → VisionDepth evidence | CONDITIONAL | V1 wrapper and V2 guarded adapter pass their rejection paths; no legal local MP4 was found, so `VIDEO_SOURCE_REQUIRED` is the only real-media result |
| VisionDepth V2 guarded adapter | CONDITIONAL | `backend/visiondepth_v2/`; 4 tests and compile pass; camera calibration, license and authorized-video gates remain closed |
| PostgreSQL/PostGIS | NOT VERIFIED | Migration/configuration exists; live migration, seed, restart persistence, spatial query and real PostGIS instance are unverified |
| Coordinate calibration | CONDITIONAL at range level | `review/huangpu-range-calibration.md` supports range-level alignment; formal control-point/building-element calibration is `NOT VERIFIED` |
| Visual review | CONDITIONAL / `VISUAL_REVIEW` | Screenshots exist; final human comparison against `references/golden-dashboard.png` is not an acceptance result |
| 60-second core chain | PASS / CONDITIONAL | `review/e2e/60-second-chain.json`; API → WS → telemetry → event → Cesium → forecast → fallback → reconnect completed; forced outage logs are expected |
| Five-minute rehearsal | NOT RERUN IN RC1.1 | The RC0 rehearsal artifact remains historical; CCTV/AI remain placeholder-conditional |
| Production deployment / rollback rehearsal | NOT VERIFIED | No production deployment rehearsal; Git rollback anchor exists at the RC0 commit |

## 6. Verified artifacts and known deviations

Verified in the current audit:

- `python -B backend/smoke.py` — `PASS` on the final independent rerun.
- `python -m vision.smoke`, `python -m media.smoke` and `python -m compileall -q vision media` — `PASS`; media smoke honestly returned `VIDEO_SOURCE_REQUIRED` (existing RequestsDependencyWarning is non-fatal).
- `backend/visiondepth_v2`: `python -m pytest -q` — `4 passed`; compile passes; data/video smoke return `VIDEO_SOURCE_REQUIRED`; third-party review remains pending.
- `npm run typecheck` and `npm run build` — `PASS` on the final independent rerun; Vite emitted only the existing large-chunk warning.
- `review/e2e/api-realtime-browser-smoke.json` — `PASS`: live depth 34.5cm, REST fallback depth 41.2cm, reconnected depth 43.3cm; polling observed then stopped.
- `review/e2e/60-second-chain.json` — `PASS`: core chain, telemetry values, geographic forecast switching and induced degraded/reconnect states; page errors are zero.
- `review/rc11/MAIN_PROGRESS.md` — current worker ownership, merge SHAs, independent acceptance and evidence boundaries.

Known deviations:

- Default data is fixture/demo data unless API mode is explicitly started. It is not official Shanghai realtime data, physical sensor evidence, or a production service.
- Forecast/analysis remain synthetic fixture-backed where documented; CCTV is a placeholder; VisionDepth is a baseline.
- City source binaries and generated runtime tiles remain local to the project disk and are not portable through this source commit.
- Visual screenshots are review evidence, not proof of final visual match or user acceptance.
- No LLM key, media-server credential, or PostGIS credential is part of the RC0 environment contract.
- Forecast GeoJSON, Huangpu hydro geometry and telemetry values are synthetic/demo fixtures; they prove the integration seam, not official live Shanghai data.
- VisionDepth V2 is an isolated guarded evidence adapter; it does not imply authorized video, calibrated centimetres, external model approval or production metrics.

## 7. Release checklist

- [x] `main` branch confirmed.
- [x] Main Agent stages an explicit allowlist and inspects `git diff --cached --name-status`.
- [x] Main Agent creates the canonical commit and records its SHA here and in the audit.
- [x] Secret-bearing local env and large generated/runtime classes are excluded by boundary rules.
- [x] Backend smoke, VisionDepth/video smoke and frontend typecheck/build are recorded above.
- [x] Parent runs API/WS browser smoke and fixed 1920×1080 60-second chain on the integrated tree.
- [x] Parent resolves or explicitly carries all conditional gates above.
- [x] Parent records known-good visual/build artifact and rollback SHA after commit.

## 8. Rollback

```text
Previous stable release: RC0 at `78e96e7d4a85a4aa24368bbd0465002a0097e45b`
Current source rollback point: `8c3e582`
RC0 rollback anchor: `78e96e7d4a85a4aa24368bbd0465002a0097e45b`
Recovery: use a commit-based revert after the anchor exists; do not treat ignored runtime data as a Git rollback
```
