# RC1.1 Main Progress

## Define Goal

**RC1.1 Real Perception / Productization**

保持 RC0 主链不回归：

```text
REST → WS → Telemetry → FloodPoint/Event → Cesium → NOW/+10/+30
```

本轮只交付最短可验收增量：

```text
Sensor evidence visible
VisionDepth upload/URL product seam
Huangpu River geographic layer
Sensor / selected event geographic entity
移除 screen-space 业务重复层
MP4 → frame → VisionDepth → timestamped JSON evidence
```

算法、PostGIS、真实 CCTV、正式坐标校准、模型升级没有证据时保持 `CONDITIONAL` 或 `NOT VERIFIED`，不阻塞 RC0 主链。

## Baseline

- RC0 release head: `78e96e7d4a85a4aa24368bbd0465002a0097e45b`
- RC1.1 Contract baseline: `f7c456ddade11a1828a96d02dd290d9eb4899061`
- Remote: `goat0330/shanshui-waterlogging-mvp`
- Main: only integration / release line

## Worker Ownership

| Worker | Branch | Worktree | Scope | P0 |
|---|---|---|---|---|
| Backend | `worker/rc11-backend` | `worktrees/backend-rc11` | `backend/**`, `review/backend/**` | VisionDepth API |
| Dashboard | `worker/rc11-dashboard` | `worktrees/dashboard-rc11` | Dashboard frontend scope | semantic cleanup + evidence UI |
| Cesium | `worker/rc11-cesium` | `worktrees/cesium-rc11` | Cesium scene scope + hydro assets | River + geographic entities |
| Vision/Video | `worker/rc11-vision-video` | `worktrees/vision-video-rc11` | `vision/**`, `media/**`, review evidence | video evidence pipeline |

Workers must not modify `contracts/**`; contract changes return as a proposal to Main.

## Checkpoints

- A: inspect ownership, checkpoint commit, local smoke, P0 state, blocker.
- B: independently test stable P0 and incrementally merge; Backend/Vision first.
- Freeze: no new feature/model/dependency/schema; bugfix, integration, regression, docs only.
- Final: Main independently runs RC0 regression plus new evidence checks.

## Status

```text
MAIN: ACCEPTANCE COMPLETE / RC1.1 CHECKPOINT
BACKEND: MERGED / P0 PASS / a6d9d04
DASHBOARD: MERGED / P0 PASS / 876a03e
CESIUM: MERGED / P0 PASS / 07c0d06
VISION-VIDEO: MERGED / P0 PASS CONDITIONAL / a81b5de + 79933c5
VISIONDEPTH-V2: MERGED / CONDITIONAL / 8c3e582
```

## Main Integration

- Current Main merge head before this ledger update: `1929009` (`merge(rc11): add dashboard evidence seams`).
- Integrated merge commits: backend `a6d9d04`; video evidence `8951c28`; Cesium `c86bf0b`; Dashboard `1929009`.
- All four worker worktrees remain isolated and clean at their checkpoint commits.
- Main did not modify `contracts/**` during worker merges; the frozen VisionDepth upload/URL contract remains the source of truth.

## Independent Acceptance Evidence

| Check | Result | Evidence |
|---|---|---|
| Backend REST/WebSocket/telemetry/VisionDepth | PASS | `python -B backend/smoke.py` |
| Frontend typecheck/build | PASS | `npm run typecheck`, `npm run build` |
| VisionDepth three-image baseline | PASS | `python -m vision.smoke` |
| Video evidence wrapper | CONDITIONAL | `python -m media.smoke` → `VIDEO_SOURCE_REQUIRED`; no legal MP4 present |
| API → WS → telemetry → UI | PASS | `frontend/scripts/api_realtime_browser_smoke.py` |
| WS failure → REST fallback → reconnect | PASS / CONDITIONAL | `review/e2e/api-realtime-browser-smoke.json`; page errors 0, expected network errors during forced outage |
| 60-second main chain | PASS / CONDITIONAL | `review/e2e/60-second-chain.json`; NOW/+10/+30 and fallback passed, expected outage logs |
| Legacy screen-space business layer | PASS | no `MARKER_POSITIONS`, `floodPath`, selected popup, network overlay or `.scene-overlay` business symbol under `frontend/src` |

## Evidence Boundaries

- `source=demo` / local demo city blocks is explicit when the real Shanghai Core Local tileset is unavailable.
- Huangpu River geometry is synthetic WGS84 demo GeoJSON, not official hydrography.
- VisionDepth is an OpenCV baseline/evidence adapter; production accuracy, internet-image reliability and model upgrade are `NOT VERIFIED`.
- CCTV remains a real `<video>` seam with `DEMO / PLACEHOLDER` fallback; no licensed local MP4 was found.
- Backend smoke uses memory mode. PostgreSQL/PostGIS persistence, physical ESP32/STM32, 4G/Wi-Fi and official live Shanghai feeds remain `NOT VERIFIED`.

## Next Gate

No new feature dispatch in this cycle. The remaining gate is user visual review plus, when assets/credentials become available, verification of licensed city/hydro data, legal MP4 and production VisionDepth accuracy. Main should push only this accepted integration line.

## VisionDepth V2 LeanGuard Checkpoint

- Merge: `8c3e582` (`merge(visiondepth): add guarded V2 evidence scaffold`).
- Scope is isolated to `backend/visiondepth_v2/**` and `review/backend/VISIONDEPTH_V2_PROGRESS.md`; no `contracts/**`, `backend/app/**`, `vision/**`, `media/**`, frontend or raw data changes.
- Main independent checks: `python -m pytest -q` → `4 passed`; `python -m compileall -q src tools tests` → `PASS`.
- Data gate/video smoke: `VIDEO_SOURCE_REQUIRED` because the authorized manifest and MP4 are absent; `sampledFrames=0`, `synthetic=false`.
- Third-party review: `V-FloodNet` and `flood-water-segmentation` remain pending; no source, weights, data or video were downloaded.
- V2 is a guarded research/evidence adapter only. It does not enter FastAPI routes or the dashboard and cannot be presented as real calibrated video depth.
