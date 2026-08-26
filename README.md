# 山水智鉴｜城市内涝智能防控中心 MVP

Current-state truth: `docs/06_DELIVERY_MANIFEST.md`.
Frozen MVP evidence policy: `docs/RC2_SOURCE_PROVENANCE_POLICY.md`.

## Current product shape

- 9 formal event cards = 1 realtime + 8 verified historical public-report cases.
- Historical cases never reuse current Sensor/Forecast/CCTV state.
- Same-event approved media is `CASE_SOURCE_MEDIA`; missing media/depth is valid.
- Frontend API mode uses same-origin `/api` and `/ws`, proxied to backend `8000` in local Vite runtime.
- Shanghai Water has a provisional live adapter with source-local normalization.
- CMA warning/radar is a configurable context seam; no unverified endpoint is hard-coded.
- Vision image/video share one pipeline. A verified local learned water-segmentation checkpoint can be enabled with `VISION_WATER_SEGMENTATION_CHECKPOINT`; OpenCV remains the fallback.

## Local run

```text
backend:  python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
frontend: npm run dev -- --host 127.0.0.1 --port 4173
```

For API mode set `VITE_DATA_SOURCE=api`. The frontend default API base is same-origin, so stale local `8002` routing is not canonical.

## Truth boundaries

This repository is an evidence-backed research/demo MVP, not production infrastructure. Do not conflate local-MVP approval with public redistribution/production approval. Do not label research video as Shanghai LIVE CCTV. Do not present uncalibrated visual evidence as production centimetre water depth.
