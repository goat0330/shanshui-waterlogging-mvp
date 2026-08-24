# AGENTS.md

## Project
山水智鉴｜城市内涝智能防控中心 RC2.1 Closure

当前基线：public Main 的 RC2 immutable tag 为 `b0a41d1`；本地 RC2.1 closure code checkpoint 为 `eb122f0`，待主线回归后同步远端。当前状态为 `CONDITIONAL / VISUAL_REVIEW`；不得把 demo、synthetic、research MVP 或未标定结果表述为生产能力。

## Read First
所有 Worker 开始任何实现前，按顺序阅读：

1. `docs/00_MASTER_BLUEPRINT.md`
2. `docs/01_PRODUCT_SPEC_MVP.md`
3. `docs/02_VISUAL_SCENE_SPEC.md`
4. `docs/03_ARCHITECTURE_OSS.md`
5. `contracts/openapi.yaml`
6. `contracts/schemas/`
7. `contracts/fixtures/`
8. `references/golden-dashboard.png`

## Sources of Truth

```text
Product:
docs/01_PRODUCT_SPEC_MVP.md

Visual:
references/golden-dashboard.png
> docs/02_VISUAL_SCENE_SPEC.md

Contract:
contracts/
```

Contract 的最终负责人是 Architect/Integration Worker。

Frontend / Backend Worker 不得自行修改 Contract。

## Lean-Guard

禁止因为“看起来专业”提前引入：

- 微服务；
- Kafka；
- Redis；
- K8s；
- 大型 Storybook；
- OpenAPI Codegen；
- IoT 平台；
- GB28181；
- 实时 SWMM；
- 实时 U-RNN；
- 多 Agent orchestration；
- 大型权限系统。

只有 `00_MASTER_BLUEPRINT.md` 的 Gate 明确允许后才能加入。

## Worker Ownership

### Main / Integration

负责 canonical Main、跨模块 wiring、`docs/**`、`review/**`、`.github/workflows/**`、release manifest 和最终独立验收。Main 不重新实现 Frontend / Backend / Vision 算法。

### Frontend Worker

可修改：

```text
frontend/**
review/frontend/**
```

可读取：

```text
docs/**
contracts/**
references/**
```

禁止修改：

```text
backend/**
contracts/**
docs/00_MASTER_BLUEPRINT.md
docs/03_ARCHITECTURE_OSS.md
```

### Dashboard Worker

负责 `frontend/src/App.tsx`、`frontend/src/components.tsx`、Dashboard hooks/services/types 和 `review/frontend/**`。视频 Overlay 只能消费已有 timestamped evidence contract；不得伪造 LIVE、标定厘米或修改 Cesium scene ownership。

### Cesium Worker

负责 `frontend/src/CesiumScene.tsx`、`frontend/src/scene/**` 中的 geographic scene layer 和 `review/cesium/**`。业务点必须使用 WGS84 geographic coordinates；真实 SensorState 缺失时才允许显式 FloodPoint fallback。

### Vision / Video Worker

负责 `media/**`、`backend/visiondepth_v2/**`、`review/media/**` 和明确授权的 synthetic browser evidence asset。复用 `media/video_pipeline.py`；V-FloodNet pending-license MP4、模型权重和 runtime outputs 不进入 public Git。

### Backend Worker

可修改：

```text
backend/**
spikes/api/**
review/backend/**
```

可读取：

```text
docs/**
contracts/**
```

禁止修改：

```text
frontend/**
contracts/**
references/**
```

### Architect / Integration Worker

负责：

```text
docs/**
contracts/**
spikes/cesium/**
spikes/video/**
spikes/api/**
integration/**
review/**
```

集成阶段可处理：

```text
frontend service adapter
backend adapter
env
contract compatibility
```

但不重新实现 Frontend / Backend 主模块。

## Visual Rules

- Frozen target: `references/golden-dashboard.png`
- 暗色白天，不是夜景；
- 中央 3D 城市是主角；
- 建筑压低；
- 水系突出；
- 积水比河流更突出；
- 橙色只给风险；
- 不随意更改信息层级；
- 不把中央场景缩成地图卡片。

## Contract Rules

Mock / Backend 必须：

- same field names；
- same types；
- same enum；
- same empty/error semantics。

不允许：

- Frontend 写一套“临时字段”；
- Backend 返回另一套“更合理字段”；
- 用 adapter 掩盖 Contract 语义冲突。

## Autonomous Rules

普通问题自主解决：

```text
padding
font-size
type error
build error
test error
局部组件 API
可逆代码组织
```

只在以下情况升级：

1. Product 冲突；
2. Visual 与 Golden Reference 冲突；
3. Contract 冲突；
4. 需要新增/删除核心业务；
5. 需要真实 Secret；
6. 需要付费或不可逆外部操作；
7. 许可证风险。

## Validation

任何 Worker 报告完成时必须给出：

1. changed files；
2. validation commands；
3. actual results；
4. blockers；
5. NOT VERIFIED；
6. contract differences（必须为空或明确说明）。

Build PASS 不等于 Runtime VERIFIED。

## Delivery

最终候选版本只能由 canonical integration worktree / branch 产生。

最终状态只能：

```text
PASS
CONDITIONAL
NOT VERIFIED
```
