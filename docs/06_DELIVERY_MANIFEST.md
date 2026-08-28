# DELIVERY_MANIFEST — Current MVP State

Baseline audited for this fix: `main@0cdc32903d2fbae4e2cec34c54346dd75213bcbd`.

Status: **IMPLEMENTED / CONDITIONAL / MVP-READY AFTER LOCAL RUNTIME SMOKE**.

## Product truth

- Formal events: **9** = 1 realtime event + 8 verified historical public-report cases.
- Historical cases are not current alarms and do not reuse current Sensor/Forecast/CCTV state.
- Historical media is optional; same-event approved media is `CASE_SOURCE_MEDIA`.
- Default tracked browser video is synthetic fallback only. Local research MP4 is the preferred MVP video and must be labeled non-live/research.
- Vision evidence never overwrites SensorState.

## Data/runtime

- Frontend canonical preview: `http://127.0.0.1:4173/`.
- Backend canonical local port: `8000`.
- Frontend same-origin `/api` and `/ws` proxy to backend `8000`; stale `8002` local configuration is not canonical.
- API mode degrades per domain instead of failing the entire dashboard on one endpoint.
- Historical cases fall back to the checked-in verified case registry if that provisional backend endpoint is unavailable.

## Shanghai Water

- `hybrid` live evidence previously returned 63 rainfall, 45 ponding and 55 water-level records.
- Source-local normalization absorbs field aliases and row-level malformed records without loosening internal domain models.
- Signed water-level values are accepted for water-level/forecast fields.
- Strict real mode requires the three current-observation feeds; optional water-level forecast does not collapse an otherwise usable snapshot.
- Coordinate provenance remains `SOURCE_REPORTED_XX2000_YY2000`; no WGS84 claim is added.

## Meteorology / CMA-NMC context

- Built-in MVP providers are implemented for NMC current weather, NMC Shanghai warning list, NMC radar preview, and China Weather 0–2 h minute precipitation nowcast.
- Backend owns meteorology polling (`METEOROLOGY_POLL_INTERVAL_SECONDS`, default 360 s), last-good runtime state and `meteorology.updated` WebSocket projection.
- Runtime `sourceHealth` is the authority: a provider becomes `OK` only after a successful machine-readable fetch/parse; network/schema failures remain `UNAVAILABLE`/`SCHEMA_MISMATCH` instead of being hidden by fixture data.
- NMC radar is treated as a real preview only. It remains `georeferenced=false` / `renderableInCesium=false` unless a configured metadata source supplies a trustworthy `rasterUrl + CRS + bbox`.
- The built-in 0–2 h product is point precipitation nowcast, not a flood-depth forecast and not a georeferenced radar raster.
- `CMA_WARNING_URL` and `CMA_NOWCAST_URL` remain optional override seams; blank values use the built-in public providers.
- Meteorology remains in `MeteorologyContext`; it never overwrites `FloodForecast`.

## Vision

- Image API/mask/decision path: implemented.
- Learned water segmentation candidate: **VERIFIED_FOR_RESEARCH_MVP** on held-out WebCOOS masks; the shared image/video runtime uses it when the verified checkpoint is configured or found under the project-local/sibling research data path; otherwise it falls back to OpenCV. The checkpoint is cached per process for video-frame reuse.
  - candidate IoU `0.648314`
  - OpenCV baseline IoU `0.395276`
- This is segmentation evidence, not centimetre-depth accuracy.
- Camera calibration remains NOT_VERIFIED; uncalibrated numeric depth remains null where required.

## Research media rights gate

Local research MVP use is approved by project policy. Production/public redistribution remains a separate gate. `licenseReview=pending_external_redistribution` must not be interpreted as `MVP blocked`.

## Still NOT_VERIFIED / intentionally out of this leanguard fix

- PostGIS live persistence/spatial query restart test;
- physical MQTT/device gateway;
- production auth/CORS policy;
- real Shanghai LIVE CCTV;
- georeferenced radar raster/tile overlay when no trustworthy CRS+bbox metadata source is configured;
- calibrated metric Vision depth;
- production/public redistribution clearance where separately required;
- final human visual acceptance.

## Required local smoke after applying this package

```text
python -m compileall -q backend/app
python backend/smoke_leanguard.py
cd frontend
npm run typecheck
npm run build
```

Then launch backend on `8000` and frontend on `4173` and verify the 9-event selector, API badge, history detail, non-live video label, and Shanghai Water source health.

## RC2.4 frontend visual closure addendum

- Historical selection: PASS / CONDITIONAL — dedicated historical scene card + expanded historical information panel + same-event official media panel; no realtime Sensor/Forecast/CCTV inheritance.
- Ground basemap: IMPLEMENTED — online OpenStreetMap imagery restored beneath 3D buildings and explicit road/label layers; presentation is dimmed/desaturated for the dark dashboard.
- Event title typography: IMPLEMENTED — product display normalizes intersection separator `×` to `·` without mutating source data.
- Historical media semantics: PASS — only `CASE_SOURCE_MEDIA` is shown; the FP-001 research `VISION_VIDEO` is not reused for historical cases.

## Realtime intelligence + open-source hydrodynamic path — QIXIAO_INTELLIGENCE_V7

- Live Sensor depth now feeds a process-local depth history and a robust median pairwise slope estimator; `riseRateCmMin` is no longer forced to the fixture value after sufficient telemetry samples arrive.
- `RiskAssessmentService` computes an explainable `0–100` risk index (`RULE_WEIGHTED_V1`) plus hard safety floors. The index is **not a probability**. Missing/stale evidence reduces confidence instead of silently producing NORMAL.
- `/api/v1/flood-events/{event_id}/risk` exposes the structured risk result. Event, risk, forecast and analysis are broadcast together as `event.intelligence.updated` after telemetry and after Shanghai Water / meteorology source refreshes.
- Forecast provider ladder: `SCENARIO_LIBRARY` (when `data/runtime/forecast-scenarios.json` is present and matches) → `EMPIRICAL_BASELINE` → static `SYNTHETIC_FIXTURE` before live telemetry. Empirical forecasts expose lower/upper uncertainty bounds and method metadata.
- Existing `pipeLoadPercent` remains `SCENARIO_BASELINE` until a real drainage-network telemetry/model output replaces it.
- `research/swmm` adds a research-only path around SWMManywhere + swmm_api + PySWMM. Heavy dependencies are not imported by the FastAPI runtime.
- Any SWMManywhere output is `SYNTHETIC_UDM / NOT_OFFICIAL_NETWORK / RESEARCH_MVP`; it must not be described as the official Shanghai drainage network.
