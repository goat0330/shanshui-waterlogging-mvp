# RC1.1 Dashboard Frontend Progress

Status: IMPLEMENTED slice / VISUAL_REVIEW pending

## Checkpoint 1

- Baseline: `f16e18b`
- Commit: `11fc14a` — remove duplicate screen-space scene overlays
- Scope: removed React wrapper `MARKER_POSITIONS`, hard-coded flood paths, selected popup, marker layer, and decorative network. Kept Cesium scene mount, scene atmosphere, toolbar, and depth legend.
- Validation: `npm install` completed; `npm run typecheck` PASS. Main independently reported `npm run build` PASS for this checkpoint.

## Remaining P0

- Replace the status cloud glyph with an existing dashboard statistic.
- Add explicit Sensor Evidence: sensorId, measured depth, observedAt/freshness, source, and status.
- Add the minimal contract-shaped VisionDepth upload/URL drawer shell with loading/error and observation evidence fields.
- Replace CCTV fake playback state with a real `<video>` seam and truthful DEMO/PLACEHOLDER fallback; no real-time label without legal media.

## Guardrails

- `frontend/src/CesiumScene.tsx`, `contracts/**`, `backend/**`, `vision/**`, and other worker-owned paths were not modified.
- This checkpoint is not final acceptance. Status remains `VISUAL_REVIEW`; Main/user visual review is pending.

## Checkpoint 2 — RC1.1 P0 closeout

- Changed files: `frontend/src/App.tsx`, `frontend/src/components.tsx`, `frontend/src/styles.css`, `frontend/src/hooks/useDashboardData.ts`, `frontend/src/services/visionDepthClient.ts`, `frontend/src/types.ts`.
- Sensor: EventPanel now exposes Sensor Evidence with `sensorId`, measured `depthCm`, `observedAt`, freshness-derived `ONLINE`/`STALE`/`OFFLINE`, `source`, and `waterDetected`; fixture fallback is explicitly `DEMO_DEVICE`.
- VisionDepth: same-page Drawer supports local upload and direct URL, original/mask view, loading/error/empty/ready states, and only renders frozen Observation fields. Fixture mode is contract-shaped `DEMO / SYNTHETIC`; API mode calls the frozen upload/URL endpoints.
- Forecast: NOW is labeled as the measured Sensor baseline; `+10 min` and `+30 min` remain forecast frames and do not overwrite the measured value.
- CCTV: real `<video>` seam with native controls only after media is playable; unavailable media shows `DEMO / PLACEHOLDER` and never a real-time claim.
- Validation: `npm run typecheck` PASS; `npm run build` PASS; `git diff --check` PASS. Build retains the existing Cesium chunk-size warning only.
- Contract/API/media: VisionDepth API, actual camera media, Cesium runtime, browser console, and visual screenshot review are `NOT VERIFIED` in this worker checkpoint.
- Status: `CONDITIONAL` / `VISUAL_REVIEW`; user/Main visual acceptance is still required.
