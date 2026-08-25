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
- Main post-release repair `27d2917` exposes generated water masks through a bounded PNG artifact route; upload responses now return a browser-readable `/api/v1/vision-depth/artifacts/{filename}` path.
- 保留 `source.type=url|local` 兼容字段及既有 URL HTTP/HTTPS、timeout、逐跳 redirect、MIME/size、HTML/SVG、private-target/SSRF 防护。
- `VISION_VIDEO` 仅为 Contract 预留；当前视频 evidence 仍是 Vision worker 的 local-only artifacts，本 worker 未复制或修改算法。

## Actual commands and results

```text
python -m compileall -q app tools    PASS (exit 0)
python -B smoke.py                   PASS (exit 0)
git diff --check                     PASS (exit 0; only LF/CRLF warnings)
```

Smoke 实测包含：OpenAPI provenance required/enum/nullable shape、upload 200 JSON、direct controlled URL adapter provenance、upload 后 SensorState 未变化、旧 REST/telemetry/projection/WS/Forecast/Analysis 回归、private URL/redirect/HTML/SVG/size/error/concurrency 边界；所有断言通过。运行时仅有既有 requests dependency warning，不影响 exit 0。

## Contract parity

- backend runtime response、OpenAPI 和 `contracts/schemas/vision-depth-observation.schema.json` 当前均包含 required `provenance`；Main smoke 保持 schema additional-properties guard。

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

## Main follow-up — coarse visual display value

- The shared image pipeline now emits optional `depth.approximateDepthCm` when flood is detected but no metric reference is available.
- This value is a deterministic representative of the existing visual range (for `[50, null]`, the MVP display value is `50.0`), and `qualityFlags` includes `ROUGH_VISUAL_ESTIMATE`.
- `depth.estimatedDepthCm` remains `null` in the no-reference case; the new field must not be used as calibrated sensor data or as a final passability measurement.

## RC2.2 Decision-Ready Visual Intelligence

- Main `5b3da2d` was merged without reset as merge checkpoint `e02e198`; the worker worktree was clean before sync.
- `DashboardOverview.waterloggingSituation` is optional for old clients. Its `totalEvents`, disposition counts, district ranking, depth metrics, change proxy and new-today count are projected in `FixtureRepository.get_dashboard_overview()` from the checked-in events/flood-points fixtures. `source=FIXTURE_DERIVED`; these are not Shanghai real-time values.
- Current summary sample: `totalEvents=1`, `changeVsHour=108.0`, `disposition={pending:0, handling:1, relieved:0}`, `topDistricts=[{district:黄浦区,eventCount:1}]`, metrics `{maxDepthCm:28.6, avgDepthCm:19.4, avgResponseMinutes:32.4, newToday:1}`. `avgResponseMinutes` is a fixture duration proxy because no response-latency field exists in the current fixture.
- Vision image responses retain all old fields and add optional `decision={floodDetected, decisionDepthCm, trafficStatus, recommendation}`. The shared `project_vision_decision()` helper also accepts the existing video-frame shape; the smoke uses the checked-in synthetic video frame. Thresholds are lower-inclusive: `<10 NORMAL`, `10–<20 CAUTION`, `20–<30 NOT_RECOMMENDED`, `>=30 PROHIBITED` (therefore `>=50` is also prohibited).
- The projection does not write `SensorState`, `FloodPoint.currentDepthCm`, or Forecast; it is evidence-derived and not calibrated sensor/passability truth.

RC2.2 actual commands:

```text
python -m compileall -q app tools                                      PASS (exit 0)
python -m json.tool ..\\contracts\\schemas\\dashboard-overview.schema.json    PASS (exit 0)
python -m json.tool ..\\contracts\\schemas\\vision-depth-observation.schema.json PASS (exit 0)
python -B smoke.py                                                     PASS (exit 0)
git diff --check                                                       PASS (exit 0)
```

RC2.2 NOT VERIFIED：backend 没有新增视频 ingest/public video endpoint；当前仅验证 image API 与现有 synthetic video frame 的统一 projection helper。真实 CCTV、实时许可、校准深度、生产通行决策和外部实时数据仍未验证。
