# RC2 VisionDepth provenance contract proposal

状态：`CONDITIONAL`，本文件只记录跨边界差异，未修改 `contracts/**`。

## Observed frozen Contract

`main/5954570` 与当前 worker worktree 的 `VisionDepthObservation` 均要求根级字段：

```text
imageId, source, floodDetected, depth, method, referenceObjects,
waterMaskPath, quality, qualityFlags, model, synthetic
```

根对象 `additionalProperties: false`；`source.type` 只有 `url|local`。

## RC2 request that cannot be added locally

RC2 派发要求 public output 额外包含：

```text
sourceType, sourceId, observedAt, confidence, quality, method,
evidence/mask ref, estimatedDepthCm, synthetic, licenseReview, runtimePolicy
```

其中 `sourceType=VISION_IMAGE|VISION_VIDEO` 与当前 `source.type=url|local` 语义不同；`sourceId`、`observedAt`、`licenseReview`、`runtimePolicy` 也不在冻结 schema 中。直接添加会违反根级 `additionalProperties:false`，也违反“不自行发明 public contract 字段”。

## Minimal proposal for Architect/Main

请在 `contracts/**` 中冻结一个版本化的 provenance response（或为当前 observation 增加正式可选 provenance object），明确：

- image 与 video 的 source enum 和 source identifier；
- observedAt 与 confidence 的时区/nullable 语义；
- evidence/mask reference 的 URI/path 规则；
- `licenseReview`、`runtimePolicy` 的 enum/required 语义；
- 是否继续保留当前 `source` / `depth` 结构以及兼容期。

在该 Contract 落地前，backend 只返回当前冻结的 `VisionDepthObservation`，不把 provenance 字段塞入 `model` 或其他未约定位置。

## Ownership note

Main 同时存在 `backend/visiondepth_v2/`，其当前 adapter 仍包装现有 observation，并由 `worker/visiondepth-v2-leanguard` 所有；本 worker 不复制或修改该算法/adapter。
