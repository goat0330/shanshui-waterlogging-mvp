# RC2 Cesium Truthful Geographic Demo

Date: 2026-08-23
Worktree: `worktrees/cesium-rc11`
Branch: `worker/rc11-cesium`
Dispatch baseline: `5954570`
Worker sync baseline: `832613b` (fast-forwarded from the RC1 Cesium checkpoint)

## Status

P0: PASS in the Cesium worker smoke. P1: PASS for the minimum camera, layer-toggle, fallback-status, and 1920x1080 evidence slices. The worker stayed inside Cesium ownership; no App, component, style, backend, vision, media, contract, or source-model files were edited.

During the audit Main advanced independently to `7ebb829`; the only `HEAD..main` change outside this worker was `review/backend/VISIONDEPTH_V2_PROGRESS.md`, with no Cesium ownership diff. Main is not modified by this worker.

## Geographic truth seams

- City source order remains OSM Buildings → local core → explicit demo city blocks. The local core entry is now the canonical `/data/runtime/shanghai-core/tileset.json`.
- Worker smoke has no local core asset/token, so the visible source is explicitly `DEMO CITY BLOCKS · FALLBACK`; the Main read-only smoke observed `OSM BUILDINGS · GLOBAL`.
- Huangpu River remains a default-visible ground-attached GeoJSON data source at `/demo/hydro/huangpu-river.geojson`. It has stable feature ID `HUANGPU-RIVER-DEMO-001`, WGS84 lon/lat metadata, and explicit `synthetic-demo` attribution. It is not official hydrography.
- Geographic sensor entities now carry stable `entityType`, `floodPointId`, `sensorId`, optional `eventId`, `selected`, `source`, `longitude`, `latitude`, and `coordinateSystem` properties. Their Cesium positions use WGS84 lon/lat and their labels/selection move with the camera.
- NOW/+10/+30 GeoJSON features carry `eventId=FP202506010024`, `floodPointId=FP-001`, `forecastKey`, `source=synthetic-demo`, `coordinateSystem=WGS84 lon/lat`, and `maxDepthCm`. NOW remains the current measured surface seam; forecast frames remain separate.
- Main already removed the fixed central screen-space business overlay. This worker did not reintroduce or manipulate `scene-overlay`, fixed marker coordinates, fixed flood paths, or fixed selected popups.

## Verification

- `npm run typecheck`: PASS.
- `npm run build`: PASS; 1519 modules transformed, Vite copied 389 static assets, and only the existing Cesium >500 kB chunk warning remains.
- `git diff --check`: PASS; only Git's LF/CRLF normalization warnings appeared.
- Main read-only smoke at `http://127.0.0.1:5182/`: `source=osm`, Hydro `ready`, 5 sensors, no central overlay, 1 Cesium canvas, 0 console errors.
- Worker smoke at `http://127.0.0.1:5183/` in a clean 1920x1080 tab: `source=demo`, local tileset path exposed, Hydro `ready`, 5 sensors, `selectedPointId=FP-001`, `selectedEventId=FP202506010024`, overlay count 0, canvas count 1, 6 layer tools, 2 legends, and 0 page/console errors.
- Water and depth toggles each changed `true → false → true`.
- Forecast paths loaded successfully in order: `/demo/forecast/now.geojson`, `/demo/forecast/plus10.geojson`, `/demo/forecast/plus30.geojson`; all returned `status=ready`.
- Orbit/zoom preserved source, Hydro, sensor, selected-event, and overlay state; the scene was reloaded only to restore the final evidence camera.
- Screenshot: `review/cesium/rc2-final-1920x1080.jpg`; verified dimensions `(1920, 1080)`.

## Attribution and blockers

Hydro attribution in the asset: `Shanshui MVP RC1.1 — hand-authored demo Huangpu River corridor; not official hydrography.` License note: `Project demo geometry; replace with licensed GIS before production use.`

- The real `/data/runtime/shanghai-core/tileset.json` is not present in this worker worktree; local-core rendering is NOT VERIFIED.
- OSM Buildings was observed in the Main environment, but portable token/network/deployment behavior is NOT VERIFIED in the worker environment.
- The Huangpu geometry and forecast polygons are synthetic demo fixtures, not official hydrography, survey control, live flood telemetry, or production forecast output.
- SKP conversion, formal SHP/TIN coordinate calibration, terrain, imagery productionization, real hardware telemetry, backend/API mode, and deployment are NOT VERIFIED and remain outside this worker's scope.
