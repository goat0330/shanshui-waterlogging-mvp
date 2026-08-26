# Frontend

状态：`CONDITIONAL` / `VISUAL_REVIEW`

这是山水智鉴城市内涝 MVP 的 React + TypeScript + Vite canonical frontend。它负责可复用展示组件、Contract fixture Mock、API/WebSocket mode，以及通过 `DigitalTwinScene` mount boundary 接入的 Cesium 城市底座。当前默认数据源是 fixture；API mode 和 OSM Buildings 都是单独的条件 gate。

## Run

从本目录执行：

```bash
npm install
npm run typecheck
npm run build
npm run dev
```

开发服务器启动后：

- `/`：默认 1920×1080 首页骨架
- `/?state=high-risk`：高风险首页状态
- `/?state=plus30`：Forecast +30 首页状态
- `/gallery`：组件与完整 Dashboard 状态 Gallery

## Modes and environment names

只记录名称，不把任何本地值写入 Git：

| Name | Use | Status |
|---|---|---|
| `VITE_DATA_SOURCE` | Set to `api` for backend REST/WebSocket; unset/other uses fixtures | Optional; fixture default |
| `VITE_API_BASE_URL` | API base URL; code default is local `127.0.0.1:8000` | Conditional API mode |
| backend `DATA_MODE` | Set to `hybrid` or `real` to enable the provisional Shanghai Water Bureau source adapter | Conditional live-source mode; fixture default |
| `VITE_CESIUM_ION_TOKEN` | OSM Buildings access | Optional for local Huangpu fallback; value must remain local/ignored |
| `VITE_DEMO_VIDEO_URL` | Local-only verified MP4 served from ignored `public/runtime/` | Optional; default is tracked synthetic browser evidence |
| `VITE_DEMO_VIDEO_OVERLAY_URL` | Local-only timestamped VisionDepth overlay JSON | Optional; must match `VITE_DEMO_VIDEO_URL` |

Example API-mode setup uses only local, non-secret configuration names:

```powershell
$env:VITE_DATA_SOURCE = "api"
$env:VITE_API_BASE_URL = "http://127.0.0.1:8000"
npm run dev
```

To let the API-mode dashboard consume the public Shanghai water source seam, start the backend with `DATA_MODE=hybrid`. The existing formal Contract endpoints remain fixture-backed; the frontend calls the provisional `/api/v1/external/shanghai-water` response and labels the panel as source-reported rainfall. The source field is `RAINVALUE` (“雨量值”), not silently converted to `intensityMmH`; source-reported coordinates are not independently WGS84/GCJ-02 calibrated. If the public endpoint is unavailable, the UI keeps its existing fixture/API fallback.

`VITE_CESIUM_ION_TOKEN` is not required for the local Huangpu fallback. Do not paste its value into this README, manifests, screenshots, build logs or commit messages.

To view the local research video evidence, place the verified MP4 and its derived overlay bundle under the ignored `public/runtime/` directory, set the two `VITE_DEMO_VIDEO_*` names in `.env.local`, and restart Vite. The bundle remains `research_mvp`/local-only: pending-license media is not committed, `LIVE` is not claimed, and an uncalibrated camera keeps `estimatedDepthCm=null`.

`dist/` is generated and ignored. Do not commit or distribute it; a local build can embed locally configured Cesium access material, so the release build must use the parent's secret-safe procedure.

## Evidence and limits

Mock Adapter 位于 `src/data/homeFixtures.ts`，直接读取 `../contracts/fixtures/` 的首页相关 fixture；API mode 已通过独立浏览器联调，证据为 `review/e2e/api-realtime-browser-smoke.json`，包括 WS connected、5 秒 REST fallback polling 和 reconnect。

The current scene supports an OSM Buildings path and a local Huangpu fallback. The local runtime tiles and source binaries are intentionally outside Git. The integrated browser evidence is `review/dashboard-cesium-1920x1080.png`; technical Cesium/forecast evidence is `review/e2e/rc0-cesium-geographic-smoke.json`. Neither is a final Golden Reference acceptance.

The default fixture CCTV is a tracked synthetic browser evidence asset. With the optional local runtime variables above, `CctvCard` plays a verified research MP4 and selects its timestamped VisionDepth frame evidence; it is still not a live city camera or calibrated Shanghai CCTV depth. Huangpu alignment is range-level only; formal control-point/building-element calibration is `NOT VERIFIED`. The page remains `VISUAL_REVIEW` until a human compares the integrated 1920×1080 output with `references/golden-dashboard.png`.
