# RC2.2 建筑强调版 Cesium 场景

Date: 2026-08-25
Worktree: `worktrees/cesium-rc11`
Branch: `worker/rc11-cesium`
Canonical Main: `5b3da2d32634f4618ac0c78c59a2a0cc5a9589f3`
Worker sync: fast-forward was not possible because the worker carried prior Cesium checkpoints; Main was merged without reset as `afe2107`.

## Root cause

- The visible blue field had three separate geographic sources: the synthetic Huangpu River polygon, the selected forecast GeoJSON polygon, and the dark blue Cesium globe/imagery base.
- Demo buildings were one blue-gray `#6f8fa7` translucent primitive with flat shading, so the fallback massing had weak depth and the same color family as the environmental/业务 layers.
- The forecast effect already returns `empty` when `forecastFrame.geometryUrl` is absent, so no new blue surface was added for missing geometry.

## Visual implementation

- OSM/local/demo building colors now share a light neutral/warm-gray range; OSM imagery is lower alpha, brightness, contrast, and saturation so the base recedes.
- Demo blocks use a small warm-gray palette, opaque per-instance colors, normals, and face-forward lighting to keep volume and boundaries legible while remaining an explicit demo fallback.
- Huangpu River remains a dark-blue, low-emphasis synthetic environmental layer (`zIndex=1`); forecast remains the stronger ground-attached business surface (`zIndex=2`) with NOW cyan, +10 blue, and +30 orange styling.
- Sensor/event entities, selected-point callback, layer controls, legends, and geographic forecast loading were not structurally changed.

## Evidence

- Before: `review/cesium/rc2.2-before-1920x1080.jpg` — 1920×1080.
- After: `review/cesium/rc2.2-after-1920x1080.jpg` — 1920×1080.
- Runtime at `http://127.0.0.1:5186/`: `source=demo`, safe fallback reason `token_missing+local_core_unavailable`, Hydro `ready`, SensorState `SSZJ-NODE-001` with one geographic entity, one Cesium canvas, six layer tools, two depth legends, and zero captured console errors.
- Forecast smoke: `NOW → PLUS_10 → PLUS_30` loaded `/demo/forecast/now.geojson`, `/demo/forecast/plus10.geojson`, `/demo/forecast/plus30.geojson`, each `status=ready`; final state restored to NOW.
- Water and depth layer toggles each changed `true → false → true`.

## Verification and boundaries

- `npm run typecheck`: PASS.
- `npm run build`: PASS; 1520 modules transformed and 389 static assets copied. Existing Cesium >500 kB chunk warning remains.
- `git diff --check`: PASS; Git only reported the existing LF/CRLF normalization warnings before staging.
- OSM success and real local-core rendering are NOT VERIFIED in this token-missing worker run; the OSM/local style branches are retained and were not replaced by a new model.
- Hydro and forecast assets remain synthetic demo GeoJSON, not official or surveyed data. No backend, contract, Dashboard business component, terrain, imagery productionization, material system, or SKP conversion was added.
