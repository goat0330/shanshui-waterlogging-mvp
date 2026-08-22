# Backend

状态：`PASS` memory Contract smoke 与 RC2 image provenance output；Main `d5e568b` 已批准并合入最小向后兼容 provenance contract。PostgreSQL/PostGIS 为可选 V1 persistence path，未在本机完成实测，不写成 Production Ready。

实现范围：FastAPI + Pydantic + `FixtureRepository`。默认 `REPOSITORY_BACKEND=memory`，保留现有演示路径；设置 `REPOSITORY_BACKEND=postgres` 后使用 SQLAlchemy 2.x + psycopg + GeoAlchemy2。Forecast 与 Analysis 通过 `ForecastAdapter` / `AnalysisAdapter` 读取上级 `contracts/fixtures/`，是可替换的最小内部边界。VisionDepth 通过 `VisionDepthAdapter` 调用现有 `vision/` pipeline，作为独立 evidence seam。CORS 已开放给本地前端。

Forecast Adapter 启动加载时校验 fixture 的事件存在、`frames` 顺序为 `NOW` → `PLUS_10` → `PLUS_30`、`offsetMinutes` 单调，以及 `maxDepthCm` / `affectedAreaKm2` 非负；不满足时以明确的启动 `ValueError` 失败。Analysis Adapter 当前只提供原有 Analysis fixture fallback，内部来源标记为 `DEMO_SYNTHETIC_FIXTURE`；该标记不会新增到 OpenAPI 响应，也不代表实时 AI。Forecast/Analysis 都不会改写 `riskLevel`、`riseRateCmMin` 或 `pipeLoadPercent`。

PostgreSQL 路径不调用 `Base.metadata.create_all()`。Alembic 初始 migration 创建 PostGIS extension 和 `sites`、`sensors`、`sensor_observations`、`sensor_latest_state`、`flood_points`、`sensor_flood_mappings`、`flood_events`、`forecast_frames`、`cameras`；Point/MultiPolygon 空间列均使用 SRID 4326。遥测写入在一个 transaction 内完成 observation、latest state 和 depth projection，commit 成功后才发送 `sensor.updated`。

遥测路径已按当前正式 `contracts/` 接入为 Contract smoke：单节点 `SSZJ-NODE-001` 的 `SensorRegistryEntry` 与最新 `SensorState` 只保存在进程内存中，进程重启即丢失；注册项使用 `sensorType=WATER_DEPTH`、WGS84 坐标和 `enabled=true`。`source=DEMO_DEVICE`，不代表上海官方实时数据，也不代表 ESP32/STM32、4G 或 Wi-Fi 物理接入已完成。`/ws/v1/realtime` 保留 `scenario.started`，并在 POST 成功后向已连接客户端发送 `sensor.updated`。

## 运行

在本目录执行：

```bash
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

默认使用 memory；PostgreSQL 只在已完成 migration/seed 后启用：

```powershell
$env:REPOSITORY_BACKEND = "postgres"
$env:DATABASE_URL = "postgresql+psycopg://USER:PASSWORD@127.0.0.1:5432/shanshui"
alembic upgrade head
python tools/seed_postgres.py
python -m uvicorn app.main:app --reload --port 8000
```

也可直接传非 secret 示例 URL：`python tools/seed_postgres.py --database-url postgresql+psycopg://USER:PASSWORD@127.0.0.1:5432/shanshui`。重复 seed 使用主键 upsert，不重复插入；Forecast frame 写入前已由 `ForecastAdapter` 校验。`.env.example` 仅为示例，不会被程序自动加载。

Alembic head：`0001_v1_persistence`。

## Smoke

另开终端，在本目录执行：

```bash
python -B smoke.py
```

`smoke.py` 会启动临时 Uvicorn（默认 `8765` 端口），先检查 memory 默认配置、Alembic head 和 migration 表/extension 声明，再验证正式 14 路 REST、雨量站排行、遥测 POST/GET、mapping projection、VisionDepth upload/url 与边界错误、未知 event/sensor/scene 的明确 404、非法 `depthMm` 的 422、CORS、JSON 序列化、OpenAPI 路径/枚举、模拟器快速模式，以及可用时的 `scenario.started` 与 `sensor.updated` WebSocket。可用 `SMOKE_PORT=8766 python -B smoke.py` 更换端口。该 smoke 不把 memory 结果当作 PostgreSQL persistence 验证。

## REST 路径

```text
GET /api/v1/dashboard/overview
GET /api/v1/rainfall/current
GET /api/v1/rainfall/stations/ranking
GET /api/v1/flood-points
GET /api/v1/flood-events/{event_id}
GET /api/v1/flood-events/{event_id}/forecast
GET /api/v1/flood-events/{event_id}/analysis
GET /api/v1/cameras
GET /api/v1/cameras/{camera_id}
GET /api/v1/scenarios/{scenario_id}/timeline
POST /api/v1/vision-depth/analyze/upload
POST /api/v1/vision-depth/analyze/url
POST /api/v1/telemetry/observations
GET /api/v1/sensors/{sensor_id}
```

`GET /api/v1/rainfall/stations/ranking` 返回按 `intensityMmH` 降序排列的雨量站强度排行，字段为 `stationId`、`stationName`、`intensityMmH`。当前由 `rainfall-stations-ranking.json` demo fixture 提供，Postgres path 复用同一 fixture fallback；它表达雨量站强度，不使用 `FloodPoint.depthCm`，也不代表上海官方实时数据。

遥测 POST 必填 `sensorId`、`observedAt`、`depthMm`；`sequence`、`transport`、`batteryMv`、`signalDbm` 可选。`transport` 使用 `WIFI`、`CELLULAR_4G` 或 `SIMULATOR`。服务端生成 `receivedAt`，按 `depthCm=depthMm/10`、`waterDetected=depthMm>0` 归一化，不接受或推导 `riskLevel`、`riseRateCmMin`、`pipeLoadPercent`。

GET sensor 在已注册但尚未上报时返回明确 404；上报后直接返回 `SensorState`，不再包裹 `latestObservation`。mapping fixture 将 `SSZJ-NODE-001` 投影到 `FP-001` 与 `FP202506010024`，只更新水深，不改风险等级、上涨速度或管网负荷。`SceneSensorInput` 若由其他层使用，其正式 `type` 为 `WATER_LEVEL_SENSOR`；本 backend 当前不直接输出该对象。

VisionDepth Evidence API：

```text
POST /api/v1/vision-depth/analyze/upload
POST /api/v1/vision-depth/analyze/url
```

两个端点都返回冻结 Contract 的 `VisionDepthObservation`。上传输入只接受 JPEG/PNG/WebP，当前限制为 15 MB；URL 输入只接受 HTTP/HTTPS，关闭环境代理，逐跳重新校验 redirect，并拒绝 private/local/reserved target、HTML、SVG 和不可用媒体。错误分别使用明确的 `400`、上传 `413`、上传 `415` 和 fetch/inference `502`。该结果是独立的 VisionDepth evidence，不写入 `SensorState`、`FloodPoint.currentDepthCm` 或 `FloodEvent`，也不覆盖 telemetry；`source.type` 保留 `local` 或 `url`。

Main `d5e568b` 批准的 `provenance` 为必填严格对象：image upload/url 使用 `sourceType=VISION_IMAGE`、`sourceId=imageId`、`observedAt=null`、`licenseReview=pending`、`runtimePolicy=research_mvp`。这些字段不塞入 `model`，也不参与 telemetry 或 flood projection。`VISION_VIDEO` 仅在 Contract 中预留；当前视频 evidence 仍由 Vision worker 提供 local-only artifacts，本 backend 不伪造视频 API 或真实媒体链路。现有算法是本地 OpenCV baseline，不能表述为真实生产视觉模型、实时 AI 或真实积水数据；`synthetic` 字段遵循当前 pipeline 输出，不改变这一证据边界。

## Simulator

仅使用 Python 标准库读取 `contracts/fixtures/telemetry-sequence.json`：

```bash
python tools/telemetry_simulator.py --base-url http://127.0.0.1:8000 --no-wait
python tools/telemetry_simulator.py --base-url http://127.0.0.1:8000 --realtime
```

默认快速发送；`--realtime` 才按 fixture 的 `delayMs` 等待。Forecast 仍是 synthetic fixture，不接入 SWMM、U-RNN 或真实预测模型。

## NOT VERIFIED

`CONDITIONAL`：PostgreSQL/PostGIS migration、seed、POST→restart→GET、WGS84 round-trip、`ST_DWithin` 和 forecast geometry 查询需要可用的 PostgreSQL/PostGIS 实例；本机 Docker daemon 不可用，尚未实测。

`NOT VERIFIED`：真实 ESP32/STM32、4G/Wi-Fi 物理链路、MQTT、鉴权、官方 API、真实预测模型、SWMM/U-RNN/LLM、生产部署和高并发可靠性。
