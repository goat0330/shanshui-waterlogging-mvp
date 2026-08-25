# RC2.2 Dashboard Decision Interface

Status: `IMPLEMENTED / CONDITIONAL / VISUAL_REVIEW`

## Baseline and ownership

- Main baseline: `b6ea92a` (backend/Cesium/Vision integration already merged)
- Branch: `worker/rc22-dashboard-repair`
- Worktree: `D:/研究生作业/上海城市内涝_智慧平台/worktrees/dashboard-rc11`
- Scope: `frontend/src/App.tsx`, `frontend/src/components.tsx`, `frontend/src/hooks/useDashboardData.ts`, `frontend/src/types.ts`, and this review record.
- Cesium, backend, contracts, public media, and new dependencies were not modified.

## Delivered

- Normalized backend `waterloggingSituation` into the existing frontend summary shape: total events, one-hour delta, pending/processing/mitigated, top three districts, depth, response time, and today's new events.
- The fixture path remains an honest empty-summary fallback; API mode now renders the backend summary block instead of showing an empty panel.
- Vision image decision content now reads only the optional `observation.decision` projection: detection conclusion, decision depth, traffic status, and action recommendation. The demo fixture carries `decisionDepthCm=50`, `禁止通行`, and `积水较深，建议立即封控并组织排水` while retaining `estimatedDepthCm=null` for the uncalibrated evidence path.
- Backend enum traffic statuses are mapped to Chinese product copy in the main result cards; raw range/level/provenance stays in technical details.
- Sensor main copy is now `传感器状态` with `在线/延迟/离线/未上报`, `当前实测水深`, and `最后上报`; source/provenance wording is not used as product copy.
- CCTV receives the selected frame's optional decision projection and renders the same four decision fields in a compact video overlay. Its technical frame/provenance fields are under `技术详情`; the existing non-LIVE media/source labels remain truthful.
- The Vision result tab remains the default and shows original image plus a semi-transparent mask when the mask asset is available. `原图` and `水体Mask` remain available as separate tabs.
- Gallery/fullscreen review labels now distinguish the fixture fallback from the API-backed summary and decision surfaces.

## Conditional contract boundary

- `waterloggingSituation` is normalized at the frontend hook boundary; no backend or contract file was changed.
- No old urban-status numbers are used as the new summary. The synthetic no-reference fixture decision is a product fixture, not a calibrated production estimate.

## Validation

- `npm run typecheck`: PASS
- `npm run build`: PASS; existing large Cesium bundle warning only
- `git diff --check`: PASS
- Stale product-copy scan over `frontend/src`: PASS; no `SENSOR EVIDENCE`, old sensor disclaimer, `summary pending`, or `没有 decision projection` matches.
- Backend overview smoke: PASS; local `GET /api/v1/dashboard/overview` returned HTTP 200 with `waterloggingSituation` and the expected fixture-derived values.
- Browser/API visual review: not run in this repair; exact 1920×1080 viewport remains a user review gate.
- User visual review: pending; this checkpoint is not `MATCHED`.

## NOT VERIFIED

- Real CCTV/media, calibrated centimeter accuracy, production model/runtime, Cesium runtime, and final visual match against the target/Golden remain unverified.

## Checkpoint

- Commit SHA: recorded in the worker handoff after commit.
