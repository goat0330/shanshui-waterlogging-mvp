# Backend — canonical MVP runtime

Backend local port: **8000**.

```powershell
cd backend
$env:DATA_MODE = "hybrid"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Default repository backend remains memory. PostGIS is optional production-hardening work and does not block the current MVP.

## Core/provisional routes

Formal REST/telemetry/Vision routes remain unchanged. Provisional source routes include:

```text
GET /api/v1/historical-cases
GET /api/v1/external/shanghai-water
GET /api/v1/context/meteorology
```

### Historical cases

`data/historical-cases.json` is the canonical registry for the 8 verified historical public-report cases. Each has `mvpReviewStatus=VERIFIED_FOR_MVP`. Historical cases keep `sensorId=null` and do not inherit current Forecast/LIVE camera state. Optional `media` is a same-event `CASE_SOURCE_MEDIA` object with `mvpUseStatus=APPROVED_LOCAL_MVP`.

### Shanghai Water

The adapter keeps upstream variability inside `app/shanghai_water.py`:

- canonical field alias normalization;
- row-level malformed-record skipping when usable rows remain;
- signed water-level values allowed for SSSW/YJSW;
- strict real mode requires current rainfall/ponding/water-level feeds;
- water-level forecast is optional context and does not collapse a usable real snapshot;
- coordinate provenance remains `SOURCE_REPORTED_XX2000_YY2000` until independently verified.

### Meteorology / CMA

`MeteorologyContext` composes Shanghai rainfall and optional warning/nowcast metadata. Configure only verified machine-readable endpoints:

```text
CMA_WARNING_URL=
CMA_NOWCAST_URL=
CMA_TIMEOUT_SECONDS=8
```

If no endpoint is configured, CMA health remains `NOT_VERIFIED`. The backend does not fabricate a source. Georeferenced nowcast metadata requires CRS + bbox; raw radar is not inserted into `FloodForecast`.

### Vision

Vision remains independent evidence and never overwrites SensorState. The shared image/video pipeline uses the local learned water-segmentation checkpoint only when `VISION_WATER_SEGMENTATION_CHECKPOINT` points to a valid file; otherwise it falls back to OpenCV. The held-out segmentation result does not verify metric centimetre depth.

## Smoke

```text
python -B smoke.py
python -B smoke_leanguard.py
python -m compileall -q app
```

The second smoke checks the repaired SSSW normalization, CMA metadata parser, 8-case evidence gate, canonical case-media state, and frontend/runtime reconciliation.
