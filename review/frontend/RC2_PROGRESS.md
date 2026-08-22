# RC2 Dashboard Evidence Truth

Status: `IMPLEMENTED / CONDITIONAL / VISUAL_REVIEW`

## Scope

- Baseline: Main canonical `5954570`
- Branch: `worker/rc11-dashboard`
- Worktree: `D:/研究生作业/上海城市内涝_智慧平台/worktrees/dashboard-rc11`
- Ownership: frontend evidence presentation only; `CesiumScene.tsx`, backend, vision, media, and contracts were not modified.

## P0 implementation

- `SENSOR`: the dashboard reads `SSZJ-NODE-001` through the existing frozen sensor client shape and exposes `sensorId`, measured `depthCm`, `observedAt`, freshness/status, `source=SENSOR`, and device provenance (`DEMO_DEVICE` in fixture mode).
- `VISION_IMAGE`: the existing same-page drawer keeps local upload/direct URL, loading/error/empty/ready states, original/mask view, and frozen Observation fields: flood, level, range, nullable `estimatedDepthCm`, confidence, method, quality, flags, and synthetic/source labels.
- `VISION_VIDEO`: the CCTV seam is a real `<video>` element. Missing/unplayable fixture media is shown as `VISION_VIDEO · DEMO / PLACEHOLDER`; result overlays render only when explicit overlay data is provided. No fake `LIVE` claim is added.
- `FORECAST`: `NOW` renders the sensor measured baseline; `+10 min` and `+30 min` render forecast frames. Forecast source is visible as `SYNTHETIC FIXTURE` or `ADAPTER · SYNTHETIC`; forecast values do not overwrite sensor evidence.
- Existing scene cleanup remains intact from RC1.1: no React screen-space business marker/path/popup/network layer was reintroduced.

## Changed files

- `frontend/src/App.tsx`
- `frontend/src/components.tsx`
- `frontend/src/hooks/useDashboardData.ts`
- `frontend/src/services/apiClient.ts`
- `frontend/src/services/fixtureClient.ts`
- `frontend/src/styles.css`
- `frontend/src/types.ts`
- `frontend/review/rc2-dashboard-default-1920x1080.png`
- `frontend/review/rc2-dashboard-high-risk-1920x1080.png`
- `frontend/review/rc2-dashboard-plus30-1920x1080.png`
- `frontend/review/rc2-gallery-1920x1080.png`
- `frontend/review/rc2-vision-image-drawer-1920x1080.png`
- `frontend/review/rc2-vision-image-ready-1920x1080.png`

## Validation

- `npm run typecheck`: PASS
- `npm run build`: PASS; existing Cesium bundle-size warning only
- `git diff --check`: PASS
- Browser fixture smoke at `1920x1080` for `/`, `/?state=high-risk`, and `/?state=plus30`: PASS; `scrollWidth=1920`, `clientWidth=1920`, `scrollHeight=1080`, `clientHeight=1080`, overflow `false` for all three.
- Browser evidence labels: `source=SENSOR`, `VISION_IMAGE`, `VISION_VIDEO`, `FORECAST`, `NOW SENSOR 实测`, and `+30 min FORECAST` all visible; console error list empty in fixture smoke.
- Dashboard `VISION_IMAGE` entry → direct URL → fixture observation: PASS; contract fields `floodDetected`, `level`, `estimatedDepthCm`, `confidence`, `method`, and `qualityFlags` visible, no overflow, console error list empty.
- `/gallery` opened successfully; no horizontal overflow and no browser console errors. Its vertical scroll is expected for the component review surface.

## NOT VERIFIED / blockers

- Real backend API sensor response, VisionDepth upload/URL response, and API-mode browser integration: `NOT VERIFIED` in this checkpoint.
- Legal CCTV/MP4/HLS/WebRTC media and real VisionDepth video result: `NOT VERIFIED`; fixture media remains explicitly DEMO/PLACEHOLDER.
- Cesium runtime/source calibration, Golden Reference comparison, and user's final visual acceptance: `NOT VERIFIED` / `VISUAL_REVIEW`.
- P1 state expansion is not claimed as complete.

## Checkpoint

- Commit: checkpoint committed; full SHA is reported in the handoff below.
