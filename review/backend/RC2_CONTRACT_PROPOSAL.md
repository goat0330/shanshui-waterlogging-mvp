# RC2 VisionDepth provenance contract proposal

状态：`RESOLVED BY MAIN d5e568b`，本文件保留为历史跨边界记录，未修改 `contracts/**`。

## Observed frozen Contract

此前 `main/5954570` 与 worker worktree 的 `VisionDepthObservation` 均要求根级字段：

```text
imageId, source, floodDetected, depth, method, referenceObjects,
waterMaskPath, quality, qualityFlags, model, synthetic
```

根对象 `additionalProperties: false`；`source.type` 只有 `url|local`。该历史状态已由 Main 的 `d5e568b` 向后兼容扩展。

## Approved Contract now implemented

Main `d5e568b` 已将 `provenance` 加入 `VisionDepthObservation.required`，并冻结：

```text
provenance.sourceType = VISION_IMAGE | VISION_VIDEO
provenance.sourceId = non-empty string
provenance.observedAt = date-time | null
provenance.licenseReview = approved | pending | not_required
provenance.runtimePolicy = research_mvp | production
```

backend image upload/url 现按 `VISION_IMAGE` 组装该对象，保留旧 `source.type=url|local`，并不把 provenance 塞入 `model`。

## Remaining boundary note

`VISION_VIDEO` 仍仅为 schema 预留；当前视频 evidence 由 Vision worker 的 local-only artifacts 提供，本 worker 不修改算法或媒体原始数据。正式 Contract 文件仍由 Main/Architect 所有，本 worker 未修改 `contracts/**`。

审计合入后的 Main tree 还显示 `contracts/schemas/vision-depth-observation.schema.json` 保留旧 required 集；本 worker 按边界未改该 Contract-owned 文件。若该 JSON 也是 canonical schema，需要 Main/Architect 后续同步 `provenance`，backend 本轮只以已批准的 OpenAPI/runtime shape 做 smoke。

## Ownership note

Main 同时存在 `backend/visiondepth_v2/`，其当前 adapter 仍包装现有 observation，并由 `worker/visiondepth-v2-leanguard` 所有；本 worker 不复制或修改该算法/adapter。
