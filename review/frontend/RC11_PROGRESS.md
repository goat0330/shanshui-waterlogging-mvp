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
- Replace CCTV fake playback state with a real `<video>` seam and truthful DEMO/PLACEHOLDER fallback; never show LIVE without legal media.

## Guardrails

- `frontend/src/CesiumScene.tsx`, `contracts/**`, `backend/**`, `vision/**`, and other worker-owned paths were not modified.
- This checkpoint is not final acceptance. Status remains `VISUAL_REVIEW`; Main/user visual review is pending.
