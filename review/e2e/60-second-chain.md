# RC0 60-second chain

Status: `PASS`

| Elapsed (s) | Step | Evidence |
|---:|---|---|
| 26.5 | initial | badge=API DATA · WS CONNECTED, scene_source=osm |
| 28.3 | fp001-selected | event=FP-001, event_panel=人民路 × 滨江大道 |
| 29.8 | telemetry-12cm | response_depth_cm=12.0, ui_depth=12.0cm |
| 30.7 | telemetry-28-6cm | response_depth_cm=28.6, ui_depth=28.6cm |
| 31.5 | forecast-plus10 | forecast=PLUS_10, scene_source=PLUS_10 |
| 32.2 | forecast-plus30 | forecast=PLUS_30, scene_source=PLUS_30 |
| 32.9 | forecast-now | forecast=NOW, scene_source=NOW |
| 39.2 | degraded | badge=API DATA · WS FALLBACK |
| 44.2 | return-realtime | badge=API DATA · WS CONNECTED |

Console errors:
```text
Failed to load resource: net::ERR_CONNECTION_REFUSED
Failed to load resource: net::ERR_CONNECTION_REFUSED
Failed to load resource: net::ERR_CONNECTION_REFUSED
Failed to load resource: net::ERR_CONNECTION_REFUSED
Failed to load resource: net::ERR_CONNECTION_REFUSED
Failed to load resource: net::ERR_CONNECTION_REFUSED
WebSocket connection to 'ws://127.0.0.1:22380/ws/v1/realtime' failed: Error during WebSocket handshake: Unexpected response code: 404
```

Page errors:
```text
```
