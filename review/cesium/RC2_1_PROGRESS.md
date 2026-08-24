# RC2.1 Cesium SensorState Geographic Entity

Date: 2026-08-24
Worktree: `worktrees/cesium-rc11`
Branch: `worker/rc11-cesium`
Canonical baseline: `b0a41d1` (`rc2-evidence-demo`)

## Scope and implementation

- `CesiumScene` now accepts an optional `sensor?: SensorState | null` without changing `App.tsx`, `components.tsx`, or `types.ts`.
- When `sensor` is present, the scene ignores the `FloodPoint[]` marker list and creates exactly one Cesium geographic entity. The sensor-derived input ID is `SSZJ-NODE-001`, producing the stable entity ID `geographic-sensor-SSZJ-NODE-001`.
- The SensorState entity stores `sensorId`, `siteId`, input `depthCm`, WGS84 lon/lat coordinates, `coordinateSystem=WGS84 lon/lat`, `source`, `eventId`, and `fallback=false` in Cesium properties. Its position is `Cesium.Cartesian3.fromDegrees(lon, lat, 0)` with ground-clamped point/label behavior.
- When no SensorState is available, the scene uses only clearly labeled `floodpoint-fallback` entities (or `event-fallback` when the point list is empty). It does not silently mix FloodPoint fallback entities with the SensorState entity.
- Current selected-point/event and NOW/+10/+30 geographic data-source paths remain unchanged; the entity click callback still returns the existing FloodPoint selection ID.

## Verification

- `npm run typecheck` from `frontend/`: PASS.
- `npm run build` from `frontend/`: PASS; 1519 modules transformed, 389 static assets copied. The existing Cesium >500 kB chunk warning remains.
- `git diff --check`: PASS; only Git's existing LF/CRLF normalization warnings were emitted.
- Focused static sensor seam assertion: PASS, 7 checks covering optional prop, sensor-derived ID, single sensor branch, explicit fallback, stable Cesium ID, input depth property, and WGS84 property.
- Runtime fallback smoke at `http://127.0.0.1:5184/`: PASS; `source=demo`, Hydro `ready`, `data-sensor-mode=floodpoint-fallback`, `data-sensor-id=none`, `data-sensor-source=floodpoint-fallback`, `data-sensor-entity-count=5`, `data-sensor-depth-cm=none`, `selectedPointId=FP-001`, `selectedEventId=FP202506010024`, `forecast=NOW/ready`, one Cesium canvas, and zero captured console errors.

## Truth boundary

- The real SensorState runtime path is **NOT VERIFIED** in the browser yet because Main/Dashboard has not passed the optional `sensor` prop through `DigitalTwinScene`; the prop seam is ready for that follow-up integration.
- The current browser smoke verifies the no-SensorState fallback path only. The fallback is demo/fixture state, not live hardware telemetry.
- No official building or hydrography calibration, real local core tileset, SKP conversion, terrain, imagery productionization, backend/API integration, or hardware runtime was added or claimed here.
