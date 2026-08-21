# Realtime Contract V0.1

WebSocket:

```text
/ws/v1/realtime
```

MVP 保留 `scenario.started` stub，并增加单节点遥测事件 `sensor.updated`。

统一 envelope：

```json
{
  "type": "rainfall.updated",
  "timestamp": "2025-06-01T10:24:35+08:00",
  "payload": {}
}
```

允许事件：

```text
scenario.started
sensor.updated
rainfall.updated
flood_point.updated
flood_event.updated
forecast.updated
camera.updated
analysis.updated
scenario.completed
```

`sensor.updated` payload：

```json
{
  "sensorId": "SSZJ-NODE-001",
  "siteId": "SITE-RML-BJDD",
  "coordinates": {"lat": 31.2297, "lon": 121.4874},
  "depthMm": 286,
  "depthCm": 28.6,
  "waterDetected": true,
  "observedAt": "2026-08-21T13:15:00+08:00",
  "receivedAt": "2026-08-21T13:15:01+08:00"
}
```

本轮统一约定：`sensor.updated` 是唯一的传感器实时事件名，payload 表示已经完成站点绑定与水深归一化的 `SensorState`。前端不得自行新增 `telemetry.updated`；收到后按 Sensor → FloodPoint/Event mapping 投影。`flood_point.updated`、`flood_event.updated` 仍保留为未来独立投影事件，本轮后端不额外广播。

核心投影规则：

```text
sensor.updated
→ Sensor → FloodPoint mapping
→ 更新 FloodPoint.depthCm
→ 若为当前事件，更新 FloodEvent.currentDepthCm
```

不得由本事件自动改写 `riskLevel`、`riseRateCmMin` 或 `pipeLoadPercent`。

前端必须能够：

- 忽略未知事件；
- 按 `type` 分发；
- WebSocket 不可用时继续使用 REST / Fixture；
- 不因为 WS 断开导致整个大屏失效。
