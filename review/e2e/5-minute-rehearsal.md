# RC0 5-minute rehearsal

Status: `PASS`
Elapsed: `310.3s`

| Elapsed (s) | Step | Evidence |
|---:|---|---|
| 1.6 | 00-dashboard | badge=API DATA · WS CONNECTED, scene=osm |
| 33.4 | 01-city-rainfall | status=1, rainfall=1 |
| 63.9 | 02-fp001-flyto | event=FP-001, event_panel=present |
| 94.4 | 03-telemetry-12cm | response_depth_cm=12.0, ui_depth=12.0cm |
| 125.0 | 04-telemetry-28-6cm | response_depth_cm=28.6, ui_depth=28.6cm |
| 155.7 | 05-forecast-plus10 | forecast=PLUS_10 |
| 186.6 | 06-forecast-plus30 | forecast=PLUS_30 |
| 217.6 | 07-return-now | forecast=NOW |
| 248.1 | 08-cctv-ai | cctv_panel=1, ai_panel=1, cctv_semantics=placeholder-conditional |
| 278.6 | 09-stable-realtime | badge=API DATA · WS CONNECTED |
| 309.2 | 10-final-return | badge=API DATA · WS CONNECTED, forecast=NOW |

Expected degraded/network console entries (if any):
```text
```

Page errors:
```text
```
