# Integration Worker A — Overnight RC0

Status: `completed`

## Scope and implementation

- Updated `frontend/src/hooks/useRealtimeTelemetry.ts` only for runtime behavior. On WS error/close it performs one REST reload immediately, continues REST reloads every 5 seconds, and schedules at most one WS reconnect every 5 seconds. A successful `onopen` clears the REST interval. Effect cleanup clears both timers, detaches socket handlers, and closes the active socket.
- Updated `frontend/scripts/api_realtime_browser_smoke.py` to establish the request-count baseline before forcing WS degradation, observe the immediate reload, then require a later request-count increase for the 5-second poll before accepting the UI depth. This prevents the immediate-reload/POST response boundary from producing a flaky assertion.
- The helper starts only its own memory-backed Uvicorn and Vite processes, runs a headless Chrome at 1920×1080, and cleans those processes by PID. It never reads or prints `.env.local`.
- No changes were made to contracts, event names, Contract fields, backend implementation, vision, CesiumScene, components, App.tsx, or secrets.

## Verification commands

All commands were run from the stated directories:

```text
frontend> npm run typecheck
PASS — tsc --noEmit

frontend> npm run build
PASS — vite build; the existing >500 kB chunk-size warning remains non-blocking

git> python frontend\scripts\api_realtime_browser_smoke.py
PASS — run 1; review/e2e/api-realtime-browser-smoke.json

git> python frontend\scripts\api_realtime_browser_smoke.py
PASS — run 2; review/e2e/api-realtime-browser-smoke.json

backend> python -B smoke.py
PASS — REST, CORS, telemetry POST/GET, scenario.started, sensor.updated, projection, 404/422, and simulator checks
```

The event-name/field audit found only the existing `scenario.started` and `sensor.updated` handling in the hook; no `telemetry.updated` was introduced.

## Browser/API observations

The helper ran three phases against the actual local processes:

| Phase | Observed result |
| --- | --- |
| Live | Badge `API DATA · WS CONNECTED`; POST depth `34.5 cm`; UI current depth `34.5cm`. |
| WS degraded | Backend started with `--ws none`; badge `API DATA · WS FALLBACK`; POST depth `41.2 cm`; request counter recorded 2 before fallback, 3 after the immediate reload, and 4 after the 5-second poll (`polling_request_observed: true`); UI showed `41.2cm`. |
| Reconnected | Backend restored with WS; badge `API DATA · WS CONNECTED`; flood-event requests stayed at 5 before and after 6 seconds (`polling_stopped: true`); POST depth `43.3 cm`; UI showed `43.3cm`. |

The deliberate `--ws none` phase produced one expected browser console handshake 404. Page errors were empty. This is recorded in `api-realtime-browser-smoke.json`, not suppressed or presented as a clean network run.

## Artifacts

- `review/e2e/api-realtime-browser-smoke.json`
- `review/e2e/api-realtime-live.png`
- `review/e2e/api-realtime-rest-fallback.png`
- `review/e2e/api-realtime-reconnected.png`

## Remaining gaps

- This is local API-mode evidence against the fixture-backed memory repository and local Vite dev server. Real hardware, production deployment, PostgreSQL/PostGIS persistence, and public Shanghai data remain `NOT VERIFIED`.
- REST fallback currently reuses `dashboard.reload()`, so each 5-second refresh reloads the dashboard REST snapshot rather than a dedicated sensor-only endpoint. Existing dashboard error semantics remain unchanged when REST itself is unavailable.
- No long-duration soak test was run; the browser evidence covers one disconnect/recovery cycle and the observed timer stop after reconnect.
