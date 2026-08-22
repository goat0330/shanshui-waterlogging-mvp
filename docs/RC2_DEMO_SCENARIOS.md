# RC2 Demo Scenarios

These are the two rehearsal scripts for the RC2 Evidence-Backed Demo. They describe the observable product chain; fixture/demo and unverified states must remain labeled.

## Scenario A — Sensor-driven

1. Open the dashboard in API mode and select `FP-001` / `SSZJ-NODE-001`.
2. Show the Sensor Evidence block: measured depth, observed time/freshness, node status and `source=SENSOR`.
3. Start the telemetry simulator or submit a valid telemetry observation.
4. Confirm the WebSocket update changes the sensor/current event state.
5. Confirm the selected geographic Sensor/Event entity moves or updates in Cesium without a screen-space marker.
6. Switch `NOW`, `+10 min`, and `+30 min`. `NOW` stays the current sensor value; future frames remain `FORECAST` and disclose synthetic/model status.
7. Show Analysis/Event context without changing ownership of the measured sensor value.

Expected proof:

```text
Telemetry → WS → SENSOR measured depth → Event → geographic Cesium → forecast → analysis
```

## Scenario B — Vision-driven

1. Open the Vision Image upload/URL seam or select an accepted local video evidence result.
2. Show original/frame, water mask, reference evidence, level/range, confidence, quality and method.
3. Show `source=VISION_IMAGE` or `source=VISION_VIDEO` and the provenance/runtime labels.
4. If the camera is uncalibrated, show `estimatedDepthCm=null` and `CAMERA_UNCALIBRATED`.
5. Compare the vision range/estimate with the current `SENSOR` value.
6. Confirm the Sensor Evidence value and `FloodPoint.currentDepthCm` remain unchanged.

Expected proof:

```text
Upload/video → mask/reference → level/range/confidence → evidence → compare with Sensor
```

## Rehearsal boundary

No placeholder is presented as `LIVE`. No synthetic forecast, demo city, uncalibrated visual result or pending-license source is presented as official/production data.
