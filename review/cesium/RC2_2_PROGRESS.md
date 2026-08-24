# RC2.2 Cesium Source Fallback Reason Codes

Date: 2026-08-24
Worktree: `worktrees/cesium-rc11`
Branch: `worker/rc11-cesium`
Public Main baseline: `5af4236aab489ac62a9b21803202823a9869ebc4`
Worker sync: fast-forward was not possible because the worker contained the prior Cesium checkpoint; Main was merged without reset as `d233a5b`.

## Root cause and implementation

- With no Cesium token, the OSM branch is intentionally skipped and records `token_missing` as the upstream cause.
- With a token, an OSM initialization exception records `osm_init_failed` before trying local core.
- A local core failure records `local_core_unavailable`; when it follows either upstream condition, the visible finite code is `token_missing+local_core_unavailable` or `osm_init_failed+local_core_unavailable`.
- Local success preserves the upstream reason (`token_missing` or `osm_init_failed`); OSM success explicitly clears the reason to `none`.
- `data-source-reason` exposes only the finite reason code. Local/demo source text appends the same reason code. No error object, token value, URL credential, or raw exception is rendered or logged.

## Verification

- `npm run typecheck` from `frontend/`: PASS.
- `npm run build` from `frontend/`: PASS; 1520 modules transformed and 389 static assets copied. The existing Cesium >500 kB chunk warning remains.
- `git diff --check`: PASS; only the existing Git LF/CRLF normalization warning was emitted.
- Focused reason-code seam assertion: PASS; 5 required seams and the finite allowed-code set were checked. Token value exposure was not observed in reason codes or the rendered `data-source-reason` value.
- Runtime smoke at `http://127.0.0.1:5185/` with the worker's token-missing environment: PASS. Observed `data-source=demo`, `data-source-reason=token_missing+local_core_unavailable`, source text `DEMO CITY BLOCKS · FALLBACK · reason=token_missing+local_core_unavailable`, Hydro `ready`, forecast `ready`, one Cesium canvas, and zero captured console errors.
- The same smoke observed the already-wired SensorState seam: `data-sensor-mode=sensor-state`, `data-sensor-id=SSZJ-NODE-001`, `data-sensor-depth-cm=28.6`, `data-sensor-entity-count=1`.

## Truth boundary

- The OSM-success branch is code-verified (`setSourceReason('none')`) but not re-run in this token-missing worker smoke; prior OSM evidence remains separate from this reason-code run.
- Local core availability is not verified; the runtime used the explicit demo fallback because `/data/runtime/shanghai-core/tileset.json` was unavailable.
- No token was printed, persisted, or added to review evidence. No building/hydro calibration, SKP conversion, backend, contract, or new dependency work was performed.
