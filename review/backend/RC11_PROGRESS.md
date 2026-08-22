# RC1.1 Backend Product Seam

状态：`PASS` P0 checkpoint，工作目录为 `worktrees/backend-rc11`，branch `worker/rc11-backend`。

## P0

- `VisionDepthAdapter` 位于 `backend/app/vision_depth.py`，只调用现有 `vision.pipeline.run_pipeline`，未复制算法。
- 已接入 `POST /api/v1/vision-depth/analyze/upload` 与 `POST /api/v1/vision-depth/analyze/url`。
- 上传与 URL 的 `source.type` 分别为 `local` 与 `url`，响应使用冻结 `VisionDepthObservation` shape。
- 已覆盖 MIME、15 MB 大小、HTTP/HTTPS URL、HTML、不可用远端媒体和 inference exception 的明确错误边界；API smoke 实测 400/413/415/502。
- Vision 结果不触碰 repository、SensorState、FloodPoint 或 FloodEvent；smoke 在 telemetry 28.6 cm 基线前后核对该事实。

## 实际验证

```text
python -m compileall -q app tools       PASS
python -B smoke.py                      PASS
```

Smoke 同时通过既有 REST/404/422/CORS/JSON/OpenAPI/Forecast/Analysis/telemetry projection、WebSocket `scenario.started` + `sensor.updated`、Vision upload/url success/error 和 simulator 回归。

## Contract / blockers

- Contract diff：`none`；未修改 `contracts/**`。
- `python-multipart` 已存在于本机运行环境，未新增 requirements 依赖；其他机器仅按当前 requirements 安装时的 multipart runtime 可用性未验证。
- P1/P2 的并发边界、PostgreSQL/PostGIS restart/spatial 验证、真实硬件/网络链路和生产部署均为 `NOT VERIFIED`。
