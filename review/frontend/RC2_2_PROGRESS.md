# RC2.2 Dashboard Decision Interface

Status: `IMPLEMENTED / CONDITIONAL / VISUAL_REVIEW`

## Baseline and ownership

- Main baseline: `5b3da2d32634f4618ac0c78c59a2a0cc5a9589f3`
- Branch: `worker/rc22-dashboard`
- Worktree: `D:/研究生作业/上海城市内涝_智慧平台/worktrees/dashboard-rc11`
- Scope: `frontend/src/App.tsx`, `frontend/src/components.tsx`, `frontend/src/styles.css`, `frontend/src/types.ts`, and this review record.
- Cesium, backend, contracts, public media, and new dependencies were not modified.

## Delivered

- Replaced the legacy `城市态势` ring and `03/12/137 + 活跃点位` presentation with an optional backend `summary` block: total events, one-hour delta, pending/processing/mitigated, top three areas, depth, response time, and today's new events.
- When Main's current overview has no `summary`, the panel stays in an explicit empty state (`SUMMARY BLOCK` / `等待城市积水汇总`) instead of inventing live values.
- Vision image decision content now reads only the optional `observation.decision` projection: detection conclusion, decision depth, traffic status, and action recommendation. `approximateDepthCm`, confidence, flags, provenance, and source IDs remain in technical details or are not rendered as product conclusions.
- CCTV receives the selected frame's optional decision projection and renders the same four decision fields in a compact video overlay. Its technical frame/provenance fields are under `技术详情`; the existing non-LIVE media/source labels remain truthful.
- The Vision result tab remains the default and shows original image plus a semi-transparent mask when the mask asset is available. `原图` and `水体Mask` remain available as separate tabs.
- Gallery/fullscreen review labels now explain that the current Main baseline intentionally exercises summary/decision empty states until the backend projection is merged.

## Conditional contract boundary

- Main `5b3da2d` still exposes the frozen overview shape without `summary`, and the VisionDepth contract still has no `decision` block. The frontend types are optional so current API/fixture data remains valid; populated decision cards are `NOT VERIFIED` until the backend response and video adapter preserve these fields.
- No old urban-status numbers are used as the new summary. No Vision estimate is promoted into `decisionDepthCm`.

## Validation

- `npm run typecheck`: PASS
- `npm run build`: PASS; existing Cesium chunk-size warning only
- `git diff --check`: PASS
- Browser local smoke: PASS for `/` and `/gallery` at the available `1280×720` browser viewport; no horizontal overflow, `/gallery` exposes 3 fullscreen review states, and the rendered Dashboard/CCTV decision labels are present. Exact 1920×1080 browser viewport was not available in this run.
- User visual review: pending; this checkpoint is not `MATCHED`.

## NOT VERIFIED

- Backend summary response and Vision decision projection are not present on the stated Main baseline.
- Populated decision-state rendering with production/API data, Cesium runtime, legal/real CCTV, and final visual match against the target/Golden remain unverified.

## Checkpoint

- Commit SHA: recorded in the worker handoff after commit.
