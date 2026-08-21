# Worker B — Cesium geographic business layer

Status: completed

## Scope delivered

- `CesiumScene` now receives the existing selected event/point/forecast values from `DigitalTwinScene`.
- Flood-point entities use `Cesium.Cartesian3.fromDegrees(lon, lat, 0)` with `HeightReference.CLAMP_TO_GROUND`; FP-001 therefore resolves to the contract anchor `(121.4874, 31.2297)`. The selected point is enlarged and labelled, and Cesium picking calls the existing `onPointSelect` callback.
- The selected `ForecastFrame.geometryUrl` is loaded with `Cesium.GeoJsonDataSource.load(..., { clampToGround: true })`. Switching `NOW`, `PLUS_10`, and `PLUS_30` removes the previous source and loads the selected geographic source. Polygon styling is geographic Cesium polygon styling, not SVG geometry.
- Existing OSM Buildings/local Huangpu fallback and `layers.base` visibility handling are unchanged. The existing React overlay remains as a visual fallback; the Cesium entities/data source are the geographic proof.

## Changed files

- `frontend/src/CesiumScene.tsx`
- `frontend/src/components.tsx`
- `frontend/public/demo/forecast/now.geojson`
- `frontend/public/demo/forecast/plus10.geojson`
- `frontend/public/demo/forecast/plus30.geojson`
- `review/cesium/worker-b-geographic-layer.md`

## Evidence and checks

1. `npm run typecheck` (from `frontend/`) — PASS.
2. `npm run build` (from `frontend/`) — PASS. Vite emitted only the existing large Cesium chunk warning; the three GeoJSON files were copied into `frontend/dist/demo/forecast/`.
3. PowerShell `ConvertFrom-Json` parse check — PASS for all three public GeoJSON files. Each is a one-feature `FeatureCollection` with a closed Polygon ring, explicit `source: synthetic-demo`, and `coordinateSystem: WGS84 lon/lat` metadata. The rings expand and differ from NOW to PLUS_10 to PLUS_30 around the contract anchor `(121.4874, 31.2297)`.
4. Local Vite HTTP smoke — PASS: `/`, `/demo/forecast/now.geojson`, `/demo/forecast/plus10.geojson`, and `/demo/forecast/plus30.geojson` returned HTTP 200 and parsed as expected.
5. Focused Playwright smoke against local Vite — PASS: one `.cesium-scene-mount`, `data-forecast-status=ready`, transitions `PLUS_30 -> NOW -> PLUS_10`, and request statuses `200` for `plus30.geojson`, `now.geojson`, and `plus10.geojson`. A camera drag/zoom gesture completed with no console or page errors.

## Acceptance caveats

- The GeoJSON is synthetic demo geometry only; it is not surveyed, calibrated, or a real Shanghai hydrodynamic result.
- The browser smoke verified source loading, key switching, and no runtime errors. It did not produce a screenshot or independently assert a pixel-level camera-orbit displacement of every polygon vertex.
- No backend, contract, realtime hook, token, or `.env` file was changed; the existing forecast fixture URLs were consumed unchanged. OSM/Ion availability and local city-tileset provenance remain outside this worker smoke gate.
