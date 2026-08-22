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
MAIN: ACTIVE
BACKEND: DISPATCHED / P0
DASHBOARD: DISPATCHED / P0
CESIUM: DISPATCHED / P0
VISION-VIDEO: DISPATCHED / P0
```
