# RC2.3 Road / Label Layer Progress

Date: 2026-08-25
Branch: `worker/rc11-cesium`

## Result

The Cesium scene no longer adds `OpenStreetMapImageryProvider` on the OSM
Buildings path. The ground is now a dark, no-label globe surface. Main roads
and sparse labels are separate geographic layers, so road geometry and text no
longer arrive as one baked raster layer.

## Runtime evidence

- Source: `osm`
- Ground: `dark-globe-no-label`
- Major roads: `/data/scene/shanghai-major-roads.geojson`, `ready`
- Road source: `OpenStreetMap contributors via Geofabrik`, `roadFallback=false`
- Road payload: 21,598 `motorway/trunk/primary` LineStrings, WGS84 lon/lat
- City labels: `ready`
- Hydro: `ready`
- Forecast: `ready`
- Sensor geographic entities: `5`
- Canvas count: `1`
- Layer toggle: base `true -> false -> true`
- Zoom/orbit: completed; source and layer states remained ready
- Console errors: `0`
- Fixed screenshot: `review/cesium/rc2.3-road-labels-1920x1080.png`

## Data boundary

The runtime road asset is derived from the supplied
`shanghai-260824-free.shp.zip` archive, layer `gis_osm_roads_free_1`. The
archive README identifies the data as OpenStreetMap data distributed by
Geofabrik, dated `2026-08-24T20:20:50Z`, under Open Database License 1.0.
The runtime filter keeps `motorway`, `trunk`, and `primary` only; the original
archive is not copied into the frontend. Attribution and the conversion
boundary are recorded in `frontend/public/data/scene/shanghai-major-roads.source.json`.

The original 7-feature synthetic GeoJSON remains available only as a runtime
fallback if the real road asset cannot be loaded. No original SKP/SHP source
file was modified.

## Validation notes

- `npm run typecheck`: PASS
- `npm run build`: PASS, 1522 modules transformed
- `git diff --check`: PASS
- Build retains the existing Cesium large-chunk warning.
- Browser emitted two existing Cesium terrain-outline/heightReference
  warnings from the current hydro/forecast entity setup; no fatal console
  errors were observed.

## Deferred

- Rotated road-name billboards: Cesium `LabelGraphics` has no rotation option;
  current labels remain sparse geographic labels without adding a canvas/SVG
  billboard implementation.
- A licensed no-label raster provider: current dark globe avoids baked labels
  without introducing a new provider or dependency.
- Secondary/tertiary road payload and camera-driven road LOD: source data is
  available in the supplied archive but deferred from the initial runtime
  payload to keep the MVP load bounded.
