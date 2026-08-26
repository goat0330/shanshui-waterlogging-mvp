# Frontend — canonical MVP runtime

Status: `IMPLEMENTED / CONDITIONAL`.

## Local API-mode run

Backend canonical port is **8000** and frontend preview/dev port is **4173**.

```powershell
# backend
cd backend
$env:DATA_MODE = "hybrid"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# frontend, second terminal
cd frontend
$env:VITE_DATA_SOURCE = "api"
npm install
npm run dev -- --host 127.0.0.1 --port 4173
```

The frontend now calls same-origin `/api/*` and `/ws/*` by default. Vite proxies them to `VITE_DEV_PROXY_TARGET`, default `http://127.0.0.1:8000`. `VITE_API_BASE_URL` is only needed for an explicit cross-origin deployment.

## Degraded mode

One failed API domain no longer collapses the entire dashboard. Static verified domains may fall back independently. Current sensor state is never fabricated in API mode; before telemetry it may legitimately be absent.

## Historical events

The formal product set is 1 realtime event + 8 verified historical public-report cases. Historical cases are not current alarms and do not reuse Sensor/Forecast/CCTV. Missing depth or media is valid. Same-event approved media is `CASE_SOURCE_MEDIA`.

## Video

Tracked `/demo/video/flood_cam_017.mp4` is a synthetic browser fallback. For the MVP demonstration, use the verified local research MP4/overlay via:

```text
VITE_DEMO_VIDEO_URL=/runtime/vision-video/...
VITE_DEMO_VIDEO_OVERLAY_URL=/runtime/vision-video/....json
```

Research video must remain non-live/research and must not be labeled Shanghai LIVE CCTV.

## RC2.4 visual closure

Cesium keeps `baseLayer:false` at Viewer construction but the product now immediately adds an online OpenStreetMap imagery layer as the geographic ground surface. The imagery is dimmed/desaturated so the explicit major-road, city-label, event, sensor and forecast layers remain visually dominant. Historical selections use a dedicated historical event card plus same-event `CASE_SOURCE_MEDIA`; they never inherit the FP-001 research video, current SensorState or Forecast.
