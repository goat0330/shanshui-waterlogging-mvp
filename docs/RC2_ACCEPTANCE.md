# RC2 Acceptance Matrix

Main maintains this matrix after independent reruns. Worker self-reports are evidence, not final acceptance.

## Regression and integration

| Gate | Status | Evidence / boundary |
|---|---|---|
| Backend compile/smoke | PASS | `python -B backend/smoke.py`; REST, WebSocket, telemetry, forecast, analysis, upload, URL safety and non-overwrite checks |
| Frontend typecheck/build | PASS | `npm run typecheck`; `npm run build`; Cesium large-chunk warning only |
| Vision image smoke | PASS | `python -m vision.smoke`; 3 existing image evidence cases |
| Real video smoke | PASS / CONDITIONAL | 4 usable MP4, 25 sampled frames; 2 of 6 source files are genuinely 11 frames and remain rejected |
| API-mode browser chain | PASS | `review/e2e/api-realtime-browser-smoke.json` |
| WebSocket fallback/reconnect | PASS | live WS → REST polling fallback → reconnect; induced network errors are expected evidence |
| Cesium geographic scene/orbit/zoom | PASS / CONDITIONAL | clean controlled smoke passes; real Core Local/official hydro calibration is not verified |
| NOW/+10/+30 | PASS / CONDITIONAL | geographic GeoJSON surfaces switch in controlled smoke; values remain `NOW=SENSOR`, future=`FORECAST` |
| 60-second chain | PASS | `review/e2e/60-second-chain.json`; page errors zero |
| 5-minute rehearsal | PASS / CONDITIONAL | `review/e2e/5-minute-rehearsal.json`; CCTV/AI remain placeholder-conditional |

## Evidence and provenance

| Gate | Status | Evidence / boundary |
|---|---|---|
| Upload response provenance | PASS | API response and OpenAPI/JSON schema include `sourceType`, `sourceId`, `observedAt`, `licenseReview`, `runtimePolicy` |
| URL safety | PASS | HTTP/HTTPS, DNS/private-target, timeout, MIME, size and redirect guards; `trust_env=false` |
| Vision does not overwrite sensor | PASS | backend smoke verifies upload does not change SensorState/FloodPoint |
| Video frame evidence | PASS / CONDITIONAL | 25 readable frame JSON, masks, timestamps and overlay metadata; uncalibrated depth is null |
| Source manifest | PASS | 6 public metadata rows with URL/project/hash/policy; runtime manifest is outside Git |
| Pending-license binaries/weights absent from Git | PASS | Git file audit shows no MP4, raw runtime video, model weight or V2 output tree |

## Dashboard and human review

| Gate | Status | Evidence / boundary |
|---|---|---|
| Source labels | PASS / VISUAL_REVIEW | Dashboard separates `SENSOR`, `VISION_IMAGE`, `VISION_VIDEO`, `FORECAST`; final legibility is user review |
| Measured/visual/forecast separation | PASS | NOW uses sensor baseline; future frames use forecast values; vision never overwrites sensor |
| No fake LIVE / meaningless overlay | PASS / VISUAL_REVIEW | CCTV fallback is explicitly `DEMO / PLACEHOLDER`; final visual interpretation belongs to user |
| 1920×1080 states | PASS / VISUAL_REVIEW | default/high-risk/+30/gallery screenshots have no critical overflow; user golden comparison remains open |

## Scenarios and release

| Gate | Status | Evidence / boundary |
|---|---|---|
| Scenario A Sensor-driven | PASS | API/WS → 12cm/28.6cm → FP-001/event → geographic forecast → fallback/reconnect; 60s and 5m evidence |
| Scenario B Vision-driven | PASS / CONDITIONAL | `review/e2e/vision-image-browser-smoke.json` proves API upload → VisionDepth observation → provenance UI with Sensor 28.6cm unchanged; video feed and calibrated cm remain unavailable |
| README / AGENTS / Delivery Manifest | PASS | current RC2 docs describe actual code/evidence boundaries |
| Source manifest/download instructions | PASS | public metadata only; binaries remain local-only |
| Git clean / no secrets | PENDING | final staged allowlist and secret/runtime audit before release tag |
| `rc2-evidence-demo` tag | PENDING | create only after final Main commit and independent rerun |

## Allowed final status

```text
PASS / RC2 EVIDENCE-BACKED DEMO / VISUAL_REVIEW
CONDITIONAL / RC2
BLOCKED
```

This release is not a production deployment, not a calibrated water-depth model, not official live Shanghai data, and not a final third-party redistribution approval.
