# 山水智鉴 RC0 独立验收

日期：2026-08-22  
验收角色：Main Agent（独立复跑）；视觉最终验收由用户执行  
目标：API → WebSocket → Telemetry → FloodPoint/Event → Cesium geographic marker → NOW/+10/+30 → fallback/reconnect

## 结果

**PASS — RC0 TECHNICAL / VISUAL_REVIEW**

这表示 RC0 的展示技术主链已经在本地 API mode 可复现；它不表示官方实时数据、真实传感器、真实 CCTV、正式坐标校准或生产部署已经完成。

## P0 acceptance matrix

| Gate | Status | Independent evidence / boundary |
|---|---|---|
| G0 Git baseline | CONDITIONAL until commit | `main` confirmed; ignore and secret boundary audited; canonical commit still pending |
| G1 Backend smoke | PASS | `python -B backend/smoke.py` |
| G2 Frontend typecheck/build | PASS | `npm run typecheck`; `npm run build` |
| G3 API-mode browser | PASS | `review/e2e/api-realtime-browser-smoke.json` |
| G4 WebSocket connected | PASS | live and reconnected badge `API DATA · WS CONNECTED` |
| G5 Telemetry visible update | PASS | API response/UI pairs 34.5cm, 41.2cm fallback, 43.3cm reconnected |
| G6 FP-001 geographic marker | PASS (technical) | Cesium entity uses WGS84 demo coordinates; `review/e2e/rc0-cesium-geographic-smoke.json` |
| G7 NOW/+10/+30 geographic surface | PASS (technical) | three GeoJSON requests HTTP 200; all forecast states ready |
| G8 Degraded/fallback | PASS | 5s REST polling observed after WS failure and stopped after reconnect |
| G9 60-second chain | PASS | `review/e2e/60-second-chain.json`; page errors empty |
| G10 Canonical commit | PENDING | stage allowlist, inspect cached diff, commit, then record SHA |
| G11 Delivery docs | PASS after this update | manifest, integration readme, frontend readme and audit updated; commit identity remains pending |

## Five-minute rehearsal

`review/e2e/5-minute-rehearsal.json` is `PASS` with elapsed time `310.3s` and empty `console_errors` / `page_errors`. The recorded checkpoints are:

1. dashboard API mode / WS connected;
2. city rainfall state;
3. FP-001 selection and EventPanel;
4. telemetry 12.0cm;
5. telemetry 28.6cm;
6. forecast PLUS_10;
7. forecast PLUS_30;
8. return to NOW;
9. CCTV and AI panels present, with CCTV explicitly `placeholder-conditional`;
10. stable realtime;
11. final NOW / WS connected state.

## Explicitly deferred or conditional

- CCTV is the existing marked placeholder; no real MP4, RTSP or GB28181 feed is claimed.
- VisionDepth is a three-image baseline with `NO_REFERENCE`; calibrated Shanghai CCTV centimetres and backend integration are open.
- PostgreSQL/PostGIS live migration, persistence and spatial query are not verified.
- FP-001 and forecast surfaces prove the geographic Cesium seam with synthetic WGS84 demo geometry; formal survey/control-point calibration is not verified.
- OSM Buildings passed local token/network smoke, but the token is local-only and portable deployment/authorization is conditional.
- Final visual comparison against `references/golden-dashboard.png` is owned by the user and remains `VISUAL_REVIEW`.

## Reproduction commands

```text
cd git/backend
python -B smoke.py

cd git
python -m vision.smoke
python -m compileall -q vision

cd git/frontend
npm run typecheck
npm run build

cd git
python review/e2e/api-realtime-browser-smoke.py
python review/e2e/rc0-cesium-geographic-smoke.py
python review/e2e/rc0-60-second-chain.py
python review/e2e/rc0-5-minute-rehearsal.py
```

The browser scripts use local ephemeral ports and clean up their own processes. They do not package `.env.local`, local runtime tiles, source city binaries, dependencies or `dist/`.
