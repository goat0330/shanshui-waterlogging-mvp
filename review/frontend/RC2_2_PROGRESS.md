# RC2.2 Dashboard Decision Interface

Status: `IMPLEMENTED / CONDITIONAL / VISUAL_REVIEW`

## Baseline and ownership

- Main baseline: `38df8df` (all four RC2.2 worker checkpoints integrated)
- Branch: `main` after parent cherry-pick
- Worktree: `D:/研究生作业/上海城市内涝_智慧平台/worktrees/dashboard-rc11`
- Scope: `frontend/src/App.tsx`, `frontend/src/components.tsx`, `frontend/src/data/homeFixtures.ts`, `frontend/src/hooks/useDashboardData.ts`, `frontend/src/styles.css`, `frontend/src/types.ts`, `frontend/src/adapters/videoEvidenceAdapter.ts`, and this review record.
- Cesium, backend, contracts, public media, and new dependencies were not modified.

## Delivered

- Normalized backend `waterloggingSituation` into the existing frontend summary shape: total events, one-hour delta, pending/processing/mitigated, top three districts, depth, response time, and today's new events.
- The legacy fixture overview now receives an explicit demo-only summary projection so the visual component is reviewable locally; API mode remains authoritative and normalizes backend `waterloggingSituation` at the hook boundary.
- Vision image decision content now reads only the optional `observation.decision` projection: detection conclusion, decision depth, traffic status, and action recommendation. The demo fixture carries `decisionDepthCm=50`, `禁止通行`, and `积水较深，建议立即封控并组织排水` while retaining `estimatedDepthCm=null` for the uncalibrated evidence path.
- Backend enum traffic statuses are mapped to Chinese product copy in the main result cards; raw range/level/provenance stays in technical details.
- Sensor main copy is now `传感器状态` with `在线/延迟/离线/未上报`, `当前实测水深`, and `最后上报`; source/provenance wording is not used as product copy.
- CCTV receives the selected frame's optional decision projection and renders the same four decision fields in a compact video overlay. Flat `frame.decision` and `frame.overlay.decision` are validated and preserved; a valid nested observation decision takes precedence. No depth is inferred from level/range.
- Research/local video uses the concise visible state `非实时视频`; raw runtime policy, source type, license, and frame metadata remain under `技术详情`.
- Added image-to-code `SceneEventCard`: click a selected scene point to open a compact event overlay with location, risk label, current depth, sensor identity/freshness, last report, and existing analysis actions. It consumes the existing frontend API/fixture data path and does not modify Cesium or backend contracts.
- Reworked image-to-code `StatusPanel` against the user-provided reference: ring-based event total and delta, three workflow cards, TOP3 area bars, and four summary metrics. The current backend/demo values remain data-driven; unavailable footer metrics from the reference are not invented.
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
- Adapter decision repro: PASS for flat `frame.decision` and `frame.overlay.decision`; existing nearest-frame/null-depth smoke remains PASS.
- Browser/API visual review: PASS on Main at `http://127.0.0.1:4173/` in API mode; summary, WS badge, Cesium scene label, video decision and image upload result were independently checked. Evidence screenshots: `review/e2e/rc22-main-1920x1080.jpg` and `review/e2e/rc22-vision-api-1920x1080.jpg`.
- SceneEventCard browser smoke: PASS; `/` point click opens the card and repeating the same point click closes it; `/gallery` exposes the selected/high-risk component state.
- Browser/API visual review remains a user review gate for the current integrated runtime.
- StatusPanel browser smoke: PASS; local `/` renders the reference structure in fixture mode with the demo-only summary projection. Screenshot review used the running 1280px browser viewport; exact 1920×1080 and user visual acceptance remain open.
- User visual review: pending; this checkpoint is not `MATCHED`.

## NOT VERIFIED

- Real CCTV/media, calibrated centimeter accuracy, production model/runtime, Cesium runtime, and final visual match against the target/Golden remain unverified.

## Bounded point-to-event integration repair (2026-08-25)

- Frontend now consumes optional `FloodPoint.eventId` and `FloodPoint.sensorId` when present; an explicit backend `null` is respected and does not fall back to a guessed event.
- The data hook loads related event/forecast/analysis/camera/sensor records by the selected point relation and keeps the existing fixture fallback for older responses.
- The selected event card and right-side sensor block show the associated sensor ID even when the backend correctly returns `404` because no latest telemetry exists; they show `未上报 / 当前暂无实测数据` rather than claiming an online sensor.
- Backend checkpoint `f7493c5` exposes the relation in memory and Postgres projections and verifies FP-001 plus null relations for FP-002 through FP-005. The local backend process used for browser verification was started on port `8001`; the older process on port `8000` still serves the pre-relation response until restarted.
- Formal `contracts/openapi.yaml` still needs the two optional nullable `eventId` and `sensorId` properties; this frontend/backend repair does not claim that contract update is complete.
- Browser/API smoke on `http://127.0.0.1:5175/` against backend `8001`: FP-001 click opened the card with `人民路 · 滨江大道`, `28.6 cm`, `SSZJ-NODE-001`, `未上报`, and three actions; console errors: `0`.

## Checkpoint

- Local-main checkpoint: `a9d369a` (frontend StatusPanel refinement cherry-picked onto the Cesium-updated local `main`).
- SceneEventCard is the bounded image-to-code addition for the selected event point; status remains `IMPLEMENTED / CONDITIONAL / VISUAL_REVIEW` pending user visual review.
- The card consumes the existing selected event, sensor, and analysis data path in API/fixture modes. The running local sensor endpoint was not verified as available; no backend contract or fallback truthfulness was changed.
- StatusPanel target source: `C:\Users\WangChi\AppData\Local\Temp\codex-clipboard-94f3bfbf-5f6b-4292-9aa2-a91ed80e0342.png`; previous implementation comparison: `C:\Users\WangChi\AppData\Local\Temp\codex-clipboard-001137d8-10af-476f-b9ae-380ff3219e8f.png`.
