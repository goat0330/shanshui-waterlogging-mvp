# RC11 Cesium Geographic Productization

Date: 2026-08-23
Worktree: `worktrees/cesium-rc11`
Branch: `worker/rc11-cesium`
Baseline: `f16e18b`

## Status

P0: PASS in the isolated worktree. The central scene now has a geographic city fallback, river data source, sensor entities, flood/forecast GeoJSON, and camera-driven FlyTo. P1 smoke slices for layer toggles, fallback parity, forecast loading, and camera movement were also exercised. No contract, backend, Dashboard component, or style files were changed.

## Implementation

- The viewer is initialized once. Changing the selected target now flies the existing viewer instead of recreating it, so geographic entities and data sources remain attached to the scene.
- OSM Buildings and the existing local tileset path remain available. When no Cesium token is present and `/data/shanghai-core/tileset.json` is unavailable, the scene explicitly falls back to `DEMO CITY BLOCKS · FALLBACK`.
- `frontend/public/demo/hydro/huangpu-river.geojson` is a small synthetic Huangpu corridor in WGS84 lon/lat. Its metadata and feature properties identify it as `synthetic-demo`, state that it is not official hydrography, and require licensed GIS replacement before production use.
- River is loaded as a low-emphasis Cesium `GeoJsonDataSource`; forecast/flood surfaces remain separate ground-attached GeoJSON and use stronger forecast colors/z-order.
- Flood points are represented by Cesium point/label entities created from WGS84 lon/lat coordinates. The entity seam stores `floodPointId`, `sensorId`, and the coordinate system in entity properties for later real sensor mapping.
- Forecast loading uses only the selected frame's `geometryUrl`. An unassociated point therefore reports `data-forecast-geometry="none"` / `data-forecast-status="empty"` instead of displaying FP-001's geometry.
- The fixed Dashboard SVG fallback is intentionally not hidden or manipulated from CesiumScene. Removal of `MARKER_POSITIONS`, `floodPath`, and the selected popup remains a Dashboard worker seam; CesiumScene exposes `data-*` state and keeps its geographic entities/data sources independent.

## Verification

- `npm run typecheck`: PASS.
- `npm run build`: PASS. Existing Cesium bundle-size warning remains (about 4.44 MB minified JS); Vite copied 389 static assets.
- `git diff --check`: PASS; only the existing LF/CRLF normalization warning was reported.
- Browser smoke at 1920x1080 on `http://127.0.0.1:5181/`: PASS with zero page/console errors in a clean tab.
- Smoke observed `data-source=demo`, `data-coordinate-system=WGS84 lon/lat`, `data-hydro-status=ready`, `data-sensor-entity-count=5`, and `data-forecast-status=ready` for FP-001/NOW.
- Layer toggles changed water and depth from `true` to `false` and back to `true`. Forecast switched to `/demo/forecast/plus30.geojson` and back to `/demo/forecast/now.geojson` with `ready` status.
- Orbit/zoom followed by selecting FP-002 and returning to FP-001 preserved the Cesium canvas and geographic layer state. FP-002 reported `geometry=none` and `status=empty` as expected.
- Evidence screenshot: `review/cesium/rc11-final-1920x1080.jpg`.

## Blockers / NOT VERIFIED

- The real local core tileset is not present in this worktree, so `local` was not observed in the browser; the active scene is explicitly demo fallback, not a real Shanghai core model.
- No Cesium Ion token was available, so OSM Buildings/remote imagery success is NOT VERIFIED in this run; the existing OSM path was preserved.
- The hydro file is synthetic demo geometry, not official Huangpu water-system GIS. Licensed GIS replacement and production attribution are NOT VERIFIED.
- SKP conversion and any production city-model integration remain outside this worker's scope and were not performed.
- The Dashboard worker still needs to remove the fixed screen-space SVG business fallback under its ownership; until then the review image can show both the legacy fallback and the new geographic scene seam.
- Real backend/API, hardware telemetry, terrain, imagery, and production deployment are NOT VERIFIED.
