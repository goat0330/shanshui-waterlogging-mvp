# MVP Acceptance Matrix — Current

This matrix is subordinate to `docs/06_DELIVERY_MANIFEST.md` and the frozen evidence policy.

| Gate | Status | Current boundary |
|---|---|---|
| 9 formal events | PASS | 1 realtime + 8 `VERIFIED_FOR_MVP` historical public-report cases |
| Historical/Sensor separation | PASS | historical cases do not inherit Sensor/Forecast/LIVE CCTV |
| Historical CASE_SOURCE_MEDIA | PASS / OPTIONAL | same-event approved media is canonical; missing media does not invalidate a case |
| Backend memory contract smoke | PASS / rerun after patch | existing smoke plus `backend/smoke_leanguard.py` |
| Frontend API routing | PASS / rerun after patch | same-origin `/api`/`/ws` → Vite proxy → backend `8000`; `8002` is non-canonical |
| Granular degraded mode | IMPLEMENTED | one failed domain no longer collapses the entire dashboard |
| Shanghai Water hybrid | PASS / CONDITIONAL | prior live evidence 63 rainfall / 45 ponding / 55 water-level records |
| SSSW strict normalization | IMPLEMENTED / local smoke | aliases, signed level and row-level invalid-source handling |
| CMA warning/nowcast seam | IMPLEMENTED / NOT VERIFIED SOURCE | provider is configurable; no endpoint is fabricated |
| Vision image API | PASS / CONDITIONAL | image → mask → decision evidence; does not overwrite sensor |
| Learned water segmentation | PASS / RESEARCH MVP | WebCOOS IoU 0.648314 vs OpenCV 0.395276 |
| Learned runtime hook | IMPLEMENTED | valid local checkpoint → shared image/video pipeline; missing checkpoint → OpenCV fallback |
| Video pipeline | PASS / LOCAL RESEARCH | 4 usable videos / 25 sampled frames; non-live/research labeling required |
| Metric centimetre Vision depth | NOT VERIFIED | camera calibration remains separate |
| PostGIS/MQTT/Auth | NOT VERIFIED / NON-BLOCKING MVP | production hardening |
| Final human visual acceptance | VISUAL_REVIEW | user gate |

Local research-video MVP use is approved by project policy. External public redistribution/production rights remain a separate gate and must not be used to block local MVP execution.
