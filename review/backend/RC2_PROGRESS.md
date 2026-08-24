# RC2 Backend Evidence API

状态：`PASS` memory backend 与 VisionDepth image provenance smoke；PostgreSQL/PostGIS、真实视频链路和生产运行保持 `NOT VERIFIED`。

## Audit and merge

- Worker worktree：`worktrees/backend-rc11`。
- Branch：`worker/rc11-backend`。
- Worker baseline：`de6c529`，审计时 worktree clean。
- Main approved Contract commit：`d5e568b`。
- 实际合入结果：fast-forward 到 `72159e2`，该 tip 包含 `d5e568b`；没有 reset、覆盖或回滚未提交改动。
- Main 同步带入的 frontend/media/visiondepth_v2 产物属于其他 worker；本轮手工修改仅限 `backend/**` 与 `review/backend/**`。

## Implemented

- `VisionDepthProvenance` 使用严格 Pydantic enums/model，且 `VisionDepthObservation.provenance` 为必填、禁止额外字段。
- upload/url image adapter 组装 `sourceType=VISION_IMAGE`、`sourceId=imageId`、`observedAt=null`、`runtimePolicy=research_mvp`；local upload 的 `licenseReview=not_required`，remote URL 的 `licenseReview=pending`。
- provenance 不写入 `model`，Vision evidence 不写 `SensorState`、`FloodPoint.currentDepthCm`、`FloodEvent` 或 telemetry projection。
- 保留 `source.type=url|local` 兼容字段及既有 URL HTTP/HTTPS、timeout、逐跳 redirect、MIME/size、HTML/SVG、private-target/SSRF 防护。
- `VISION_VIDEO` 仅为 Contract 预留；当前视频 evidence 仍是 Vision worker 的 local-only artifacts，本 worker 未复制或修改算法。

## Actual commands and results

```text
python -m compileall -q app tools    PASS (exit 0)
python -B smoke.py                   PASS (exit 0)
git diff --check                     PASS (exit 0; only LF/CRLF warnings)
```

Smoke 实测包含：OpenAPI provenance required/enum/nullable shape、upload 200 JSON、direct controlled URL adapter provenance、upload 后 SensorState 未变化、旧 REST/telemetry/projection/WS/Forecast/Analysis 回归、private URL/redirect/HTML/SVG/size/error/concurrency 边界；所有断言通过。运行时仅有既有 requests dependency warning，不影响 exit 0。

## Contract differences

- backend runtime response 与 Main `d5e568b` 更新的 `contracts/openapi.yaml` 对齐；本 worker 未修改 `contracts/**`。
- 合入后的 `contracts/schemas/vision-depth-observation.schema.json` 仍显示旧 required 集，未包含 provenance；这是 Contract-owned 文件的同步差异，本轮按边界未改，需 Main/Architect 后续确认其是否为独立 canonical schema。该差异不阻塞本轮 OpenAPI/runtime smoke，但不应宣称所有 Contract artifacts 已一致。

## NOT VERIFIED / blockers

- 公网/global URL 的 endpoint 200 未在本机验证；loopback 仅通过受控 patch 验证 adapter media path，真实 endpoint 仍按 SSRF policy 拒绝 private target。
- PostgreSQL/PostGIS migration、seed、POST→restart→GET、WGS84 round-trip、`ST_DWithin`、forecast geometry 查询。
- 真实 ESP32/STM32、4G/Wi-Fi 物理链路、MQTT、鉴权、官方 API、真实 AI/预测模型、生产部署、高并发可靠性、视频 backend public endpoint。

## RC2.1 Closure — provenance semantic repair

- local multipart upload：`licenseReview=not_required`，仅表示 API 收到用户提供的本地文件，不断言第三方许可已获批准。
- remote URL：`licenseReview=pending`；没有新增 source registry，也不把未知 URL 标记为 approved。
- `sourceType=VISION_IMAGE`、`sourceId=imageId`、`observedAt=null`、`runtimePolicy=research_mvp`、SSRF/MIME/size/redirect guards 和 Sensor/Flood ownership 均保持不变。

实际命令：

```text
python -m compileall -q app tools    PASS (exit 0)
python -B smoke.py                   PASS (exit 0)
git diff --check                     PASS (exit 0; only LF/CRLF warnings)
```

本轮 checkpoint 仅修改 `backend/app/vision_depth.py`、`backend/smoke.py` 与本文件；真实公网 URL、许可审批、生产模型和物理设备链路仍 `NOT VERIFIED`。
