# DELIVERY_MANIFEST
## 山水智鉴｜城市内涝智能防控中心 MVP RC0

> 本清单只记录可复核的当前状态。`PASS` 仅表示对应证据通过，不等于生产部署；`CONDITIONAL` 和 `NOT VERIFIED` 不得在演示中省略。

---

## 1. Candidate / canonical identity

```text
Status: CONDITIONAL / VISUAL_REVIEW
Canonical branch: main (observed)
Canonical commit: PENDING — Main Agent must create and record the integrated RC0 commit
Audit date: 2026-08-22
Viewport target: 1920×1080
Release decision: RC0 technical path independently verified; not canonical until commit and human visual review
```

There is no previous stable commit or Git rollback SHA. The first canonical commit and its rollback anchor are owned by Main Agent after integration.

## 2. Entries and startup commands

| Item | Current entry / command |
|---|---|
| Frontend | `frontend/` — `npm install`, `npm run typecheck`, `npm run dev` |
| Frontend build | `npm run build` from `frontend/` — `PASS` on the integrated tree; generated `dist/` remains ignored |
| Backend | `backend/` — `python -m pip install -r requirements.txt`, then `python -m uvicorn app.main:app --reload --port 8000` |
| Backend smoke | `python -B smoke.py` from `backend/` |
| Cesium mount | `frontend/src/CesiumScene.tsx` through the main frontend |
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
| Repository root, branch, ignore boundary | PASS | Root is `git/`; branch is `main`; secret scan emitted no values; no commit yet |
| Backend memory Contract/Telemetry smoke | PASS | `python -B backend/smoke.py`; REST, CORS, WebSocket, telemetry projection, simulator, 404/422 boundaries passed |
| Frontend TypeScript | PASS | `npm run typecheck` in `frontend/` |
| Frontend production build | NOT VERIFIED | Not rerun in audit; parent must run with secret-bearing local env excluded from generated output |
| Main local Cesium/Huangpu fallback | PASS (local smoke) | `review/e2e/rc0-cesium-geographic-smoke.json` and fixed 1920×1080 evidence; local runtime tiles remain outside Git |
| OSM Buildings | PASS (local token/network smoke) / deployment CONDITIONAL | `frontend/scripts/cesium_dashboard_smoke.py` returned 30 external Cesium responses with HTTP 200; token value is local-only and not portable |
| REST/WebSocket frontend API mode | PASS (technical) | `review/e2e/api-realtime-browser-smoke.json`; live, REST fallback polling, and reconnect all passed |
| Cesium geographic FP-001 marker | PASS (technical) | WGS84 demo point is loaded as Cesium geographic entity; formal survey/building calibration remains open |
| Cesium geographic NOW/+10/+30 surface | PASS (technical) | `review/e2e/rc0-cesium-geographic-smoke.json`; all three synthetic GeoJSON requests returned HTTP 200 and rendered ready |
| WS → REST fallback | PASS (technical) | 5s polling observed after WS failure and stopped after reconnect; induced network errors are expected evidence |
| CCTV/video | CONDITIONAL | `frontend/public/mock/cctv-placeholder.webp` and `DEMO FEED · 场景占位`; panel is present but there is no real MP4/RTSP/CCTV feed |
| VisionDepth | CONDITIONAL | V1 baseline/local public-image evidence only; Shanghai CCTV generalization, calibrated centimetres, model weights and backend integration are `NOT VERIFIED` |
| PostgreSQL/PostGIS | CONDITIONAL / NOT VERIFIED | Migration/configuration exists; live migration, seed, restart persistence, spatial query and real PostGIS instance are unverified |
| Coordinate calibration | CONDITIONAL at range level | `review/huangpu-range-calibration.md` supports range-level alignment; formal control-point/building-element calibration is `NOT VERIFIED` |
| Visual review | CONDITIONAL / `VISUAL_REVIEW` | Screenshots exist; final human comparison against `references/golden-dashboard.png` is not an acceptance result |
| 60-second core chain | PASS (technical) | `review/e2e/60-second-chain.json`; API → WS → telemetry → event → Cesium → forecast → fallback → reconnect completed |
| Five-minute rehearsal | PASS (technical) / CCTV conditional | `review/e2e/5-minute-rehearsal.json`; 11 checkpoints completed in 310.3s, CCTV/AI explicitly recorded as placeholder-conditional |
| Production deployment / rollback rehearsal | NOT VERIFIED | No deployment or previous Git rollback point exists |

## 6. Verified artifacts and known deviations

Verified in the current audit:

- `python -B backend/smoke.py` — `PASS` on the final independent rerun.
- `python -m vision.smoke` and `python -m compileall -q vision` — `PASS` (existing RequestsDependencyWarning is non-fatal).
- `npm run typecheck` and `npm run build` — `PASS` on the final independent rerun; Vite emitted only the existing large-chunk warning.
- `review/e2e/api-realtime-browser-smoke.json` — `PASS`: live depth 34.5cm, REST fallback depth 41.2cm, reconnected depth 43.3cm; polling observed then stopped.
- `review/e2e/rc0-cesium-geographic-smoke.json` — `PASS`: FP-001 Cesium mount, camera gesture, NOW/+10/+30 GeoJSON HTTP 200 and ready states.
- `review/e2e/60-second-chain.json` — `PASS`: core chain and induced degraded/reconnect states.
- `review/e2e/5-minute-rehearsal.json` — `PASS`: 310.3s, 11 checkpoints, no page/console errors.
- `review/rc0-release-audit.md` — boundary, secret, size, checklist and stale-manifest audit.

Known deviations:

- Default data is fixture/demo data. It is not official Shanghai realtime data, physical sensor evidence, or a production service.
- Forecast/analysis remain synthetic fixture-backed where documented; CCTV is a placeholder; VisionDepth is a baseline.
- City source binaries and generated runtime tiles remain local to the project disk and are not portable through the first commit.
- Visual screenshots are review evidence, not proof of final visual match or user acceptance.
- No LLM key, media-server credential, or PostGIS credential is part of the RC0 environment contract.
- Forecast GeoJSON and telemetry values are synthetic demo fixtures; they prove the integration seam, not official live Shanghai data.

## 7. Release checklist

- [x] `main` branch confirmed.
- [ ] Main Agent stages an explicit allowlist and inspects `git diff --cached --name-status`.
- [ ] Main Agent creates the canonical commit and records its SHA here and in the audit.
- [x] Secret-bearing local env and large generated/runtime classes are excluded by boundary rules.
- [x] Backend smoke and frontend typecheck are recorded above.
- [x] Parent runs frontend build and fixed 1920×1080 browser smoke on the integrated tree.
- [x] Parent resolves or explicitly carries all conditional gates above.
- [ ] Parent records known-good visual/build artifact and rollback SHA after commit.

## 8. Rollback

```text
Previous stable commit: NONE — repository had no commits before RC0
Current rollback point: preserved uncommitted workspace until canonical commit exists
RC0 rollback anchor: PENDING — fill with Main Agent's canonical commit SHA after staging
Recovery: use a commit-based revert after the anchor exists; do not treat ignored runtime data as a Git rollback
```
