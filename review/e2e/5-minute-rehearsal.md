# RC0 5-minute rehearsal

Status: `PASS`
Elapsed: `309.3s`

| Elapsed (s) | Step | Evidence |
|---:|---|---|
| 2.4 | 00-dashboard | badge=API DATA · WS CONNECTED, scene=osm |
| 33.3 | 01-city-rainfall | status=1, rainfall=1 |
| 63.8 | 02-fp001-flyto | event=FP-001, event_panel=present |
| 94.4 | 03-telemetry-12cm | response_depth_cm=12.0, ui_depth=12.0cm |
| 124.9 | 04-telemetry-28-6cm | response_depth_cm=28.6, ui_depth=28.6cm |
| 155.6 | 05-forecast-plus10 | forecast=PLUS_10 |
| 186.1 | 06-forecast-plus30 | forecast=PLUS_30 |
| 216.7 | 07-return-now | forecast=NOW |
| 247.2 | 08-cctv-ai | cctv_panel=1, ai_panel=1, cctv_semantics=placeholder-conditional |
| 277.7 | 09-stable-realtime | badge=API DATA · WS CONNECTED |
| 308.2 | 10-final-return | badge=API DATA · WS CONNECTED, forecast=NOW |

Expected degraded/network console entries (if any):
```text
Failed to load resource: the server responded with a status of 404 (Not Found)
Failed to load resource: the server responded with a status of 404 (Not Found)
```

Page errors:
```text
```
