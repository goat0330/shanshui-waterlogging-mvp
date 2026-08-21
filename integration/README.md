# Integration

状态：`PASS（技术）` / `VISUAL_REVIEW` / `CANONICALIZED`

本目录负责 Adapter、Mock → API 切换、Contract compatibility、环境变量记录和 canonical 集成边界；不在集成阶段重写 frontend/backend 主模块。当前技术主链已独立复跑通过；仓库在 `main`，canonical commit/rollback anchor 为 `9628d21cfccefdfc03cda46e0247aac8c40b79e2`。

## Current seams

- Frontend canonical entry: `frontend/`; default `VITE_DATA_SOURCE` is fixture mode.
- API mode: set the environment name `VITE_DATA_SOURCE=api`; `VITE_API_BASE_URL` defaults to the local backend at `127.0.0.1:8000`.
- Backend canonical entry: `backend/`; default `REPOSITORY_BACKEND` is in-memory `FixtureRepository`.
- PostgreSQL/PostGIS is an optional persistence path only. `DATABASE_URL` is required for that path, but live migration/seed/restart/spatial-query evidence remains `NOT VERIFIED`.
- `VITE_CESIUM_ION_TOKEN` is only for the separately verified OSM Buildings path. Local Huangpu runtime data stays outside Git.

## Current acceptance boundary

| Area | Status | Evidence / limit |
|---|---|---|
| Backend memory contract and telemetry | `PASS` | `python -B backend/smoke.py` passed REST, CORS, WebSocket, telemetry projection, simulator and error boundaries |
| Frontend typecheck | `PASS` | `npm run typecheck` in `frontend/` |
| Frontend API-mode browser integration | `PASS` | `review/e2e/api-realtime-browser-smoke.json`; live, REST fallback polling and reconnect passed |
| Cesium geographic business layer | `PASS` (technical) | `review/e2e/rc0-cesium-geographic-smoke.json`; FP-001 and NOW/+10/+30 synthetic WGS84 layers ready |
| 60-second / five-minute chain | `PASS` (technical) | `review/e2e/60-second-chain.json` and `review/e2e/5-minute-rehearsal.json` |
| Forecast/analysis source | `CONDITIONAL` | Fixture-backed; does not represent a live model |
| CCTV/video | `NOT VERIFIED` | Current UI uses a marked placeholder, not a real feed |
| VisionDepth | `CONDITIONAL` | Baseline/local evidence only; production accuracy and backend integration are open |
| Formal coordinate calibration | `NOT VERIFIED` | Huangpu range-level mapping exists; control-point/building match does not |
| Visual review | `CONDITIONAL` / `VISUAL_REVIEW` | Screenshots are evidence; Golden Reference comparison is still a human gate |

## Handoff checklist

1. Done: stage an explicit file allowlist and inspect `git diff --cached --name-status`.
2. Done: keep `.env.local`, `data/source`, `data/runtime`, local Cesium tiles, `node_modules`, `dist`, `.vite`, `__pycache__`, `.codex`, and generated review ZIPs out of the first commit.
3. Done: run the integrated frontend build/browser smoke without copying a local secret into generated artifacts.
4. Done: record branch, canonical commit SHA, startup commands, environment names (never values), open conditional gates, and rollback anchor in `docs/06_DELIVERY_MANIFEST.md`.
