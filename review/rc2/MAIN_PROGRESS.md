# RC2 Main Progress

## Define Goal

`RC2 EVIDENCE-BACKED DEMO RELEASE`

收口一条可以正式录制 5 分钟演示的视频主线：

```text
Sensor measured depth
+ Vision image/video evidence
+ Forecast
+ Cesium geographic scene
+ Dashboard source truth
```

每个数值必须能区分 `SENSOR`、`VISION_IMAGE`、`VISION_VIDEO`、`FORECAST`，并保留 confidence、quality、synthetic、licenseReview 和 runtime policy。视觉结果不得覆盖传感器实测值。

## Baseline

- Main baseline: `5954570` (`main`)
- Public repository: `goat0330/shanshui-waterlogging-mvp`
- Previous release state: RC1.1 technical path + VisionDepth research MVP
- Current local video evidence: 6 manifest entries; 4 pass the >=30-frame gate; 2 source files genuinely contain 11 frames and remain rejected
- Camera state: uncalibrated; `estimatedDepthCm=null`, `CAMERA_UNCALIBRATED`
- Runtime policy: `research_mvp=true`, `production=false`, `redistribution=false`

## Worker Ownership

| Worker | Existing thread | Ownership | RC2 state |
|---|---|---|---|
| Cesium | `01a022d3-0777-7742-907d-85ee96bc2bed` | CesiumScene, scene adapters, hydro/forecast geographic assets, `review/cesium` | DISPATCHED |
| Backend | `01a02258-3560-7f73-8187-771c41a8968e` | `backend/**`, `review/backend/**` | DISPATCHED |
| Dashboard | `01a02258-9e68-74f3-b2c7-914477e82389` | Dashboard source, hooks/services/types, `review/frontend` | DISPATCHED |
| Vision/Video | `01a02504-912d-7b40-98c0-6247eed72720` | existing VisionDepth/video ownership, local manifest/instructions, `review/vision`/`review/media` | DISPATCHED |

Workers use their existing isolated branches/worktrees. Main is the only integration and release line. `contracts/**` is frozen unless Main explicitly reviews a proposal.

## RC2 P0

- Backend VisionDepth upload and URL product seam, safe ingest, provenance output, no Sensor overwrite.
- Dashboard measured/vision/forecast semantics, Sensor Evidence, Vision Image/Video states, no fake LIVE.
- Cesium City + Huangpu River + Sensor + FloodPoint/Event + NOW/+10/+30 as geographic entities.
- Real MP4 evidence: decode, frames, masks, reference, level/range, timestamped JSON, overlay metadata and summary.
- Two demo scenarios: Sensor-driven and Vision-driven.
- RC1 regression, API-mode browser chain, 60-second chain and 5-minute rehearsal.

## Provenance Boundary

Pending-license research assets may run locally, but public Git must contain only source URL/project, manifest, download instructions, optional safe hash and code. Do not commit original MP4, model weights, full datasets or runtime outputs. `production=false` and `redistribution=false` remain explicit.

## Long-Run Checkpoints

```text
T+0       entry audit / dispatch
T+2.5h    Checkpoint A: ownership, P0 tests, blockers
T+5h      Checkpoint B: independent acceptance, incremental merge
T+6h      Main shared wiring
T-90min   feature freeze: no new model/dependency/page/contract field
T-60min   Scenario A/B, 60s chain, 5min rehearsal, docs, release
```

Any external blocker lasting more than 20 minutes is recorded as `NOT VERIFIED` and gets a bounded fallback; it does not expand the scope.

## Acceptance Status

```text
RC2: IN_PROGRESS
CESIUM: DISPATCHED
BACKEND: DISPATCHED
DASHBOARD: DISPATCHED
VISION_VIDEO: DISPATCHED
VISUAL: VISUAL_REVIEW (human acceptance)
```

Final status may only be `PASS / RC2 EVIDENCE-BACKED DEMO / VISUAL_REVIEW`, `CONDITIONAL / RC2`, or `BLOCKED`. No production-ready, arbitrary-image centimeter-depth, or final-public-license claim is allowed without evidence.
