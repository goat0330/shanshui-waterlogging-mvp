# RC0 60-second chain

Status: `PASS`

| Elapsed (s) | Step | Evidence |
|---:|---|---|
| 37.3 | initial | badge=API DATA · WS CONNECTED, scene_source=osm |
| 38.4 | fp001-selected | event=FP-001, event_panel=人民路 × 滨江大道 |
| 38.9 | telemetry-12cm | response_depth_cm=12.0, ui_depth=12.0cm |
| 39.5 | telemetry-28-6cm | response_depth_cm=28.6, ui_depth=28.6cm |
| 40.3 | forecast-plus10 | forecast=PLUS_10, scene_source=PLUS_10 |
| 41.0 | forecast-plus30 | forecast=PLUS_30, scene_source=PLUS_30 |
| 41.7 | forecast-now | forecast=NOW, scene_source=NOW |
| 48.0 | degraded | badge=API DATA · WS FALLBACK |
| 53.1 | return-realtime | badge=API DATA · WS CONNECTED |

Console errors:
```text
Failed to load resource: net::ERR_CONNECTION_REFUSED
Failed to load resource: net::ERR_CONNECTION_REFUSED
Failed to load resource: net::ERR_CONNECTION_REFUSED
Failed to load resource: net::ERR_CONNECTION_REFUSED
Failed to load resource: net::ERR_CONNECTION_REFUSED
Failed to load resource: net::ERR_CONNECTION_REFUSED
WebSocket connection to 'ws://127.0.0.1:64833/ws/v1/realtime' failed: Error during WebSocket handshake: Unexpected response code: 404
```

Page errors:
```text
```
