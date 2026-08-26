# RC2.4 — Render Public Demo

## Baseline

```text
goat0330/shanshui-waterlogging-mvp
main@6294df33cea078fcc52899089c3aa5053a1ef6bd
```

This round is deployment-only.

## Public topology

```text
Render HTTPS
  ↓
Nginx :$PORT
  ├─ /              → React/Vite/Cesium
  ├─ /api/*         → FastAPI :8000
  ├─ /ws/*          → FastAPI WebSocket :8000
  ├─ /media/*       → /app/media
  ├─ /healthz       → backend Dashboard health
  └─ /openapi.json  → FastAPI OpenAPI
```

## Default environment

```text
REPOSITORY_BACKEND=memory
DATA_MODE=hybrid
VITE_DATA_SOURCE=api
VITE_API_BASE_URL=
VITE_CESIUM_ION_TOKEN=<set in Render>
MEDIA_BUNDLE_REQUIRED=false
```

`VITE_API_BASE_URL` is intentionally empty because current frontend supports same-origin `/api` and `/ws`.

## First public deploy without media Release

This package can deploy even before `cloud-demo-assets-v1` exists.

Why:
- `MEDIA_BUNDLE_REQUIRED=false`
- current tracked browser demo remains at `/demo/video/flood_cam_017.mp4`
- current historical case media can still use official public URLs
- Vision falls back to OpenCV when no learned checkpoint is present

This is useful for obtaining the final Render domain first.

## Second deploy with public media Release

Create:

```text
Tag: cloud-demo-assets-v1
Asset: qixiao-demo-media-v1.zip
```

Recommended ZIP root:

```text
video/
  current/
    flood_cam_017.mp4
    flood_cam_017.overlay.json
  research/
    ...
historical/
  SH-FLOOD-2023-0722-HK-01/
    01.jpg
    02.png
  SH-FLOOD-2025-0730-HK-01/
    ...
models/
  candidate-water-segmentation.joblib
manifest.json
```

Then:
1. keep `MEDIA_BUNDLE_URL` pointing to the Release asset;
2. set `MEDIA_BUNDLE_SHA256`;
3. set `MEDIA_BUNDLE_REQUIRED=true`;
4. redeploy.

The Docker build will:
- download the Release;
- verify SHA256 when configured;
- localize historical image URLs inside the frontend build copy;
- point CAM-017 to `/media/video/current/flood_cam_017.mp4` when present;
- auto-enable the learned checkpoint when the expected joblib file is present.

## Cesium ion

Create a dedicated public-demo token.

Use:
- only required read permissions/assets;
- Allowed URL = final `https://<service>.onrender.com`.

Set it in Render as:

```text
VITE_CESIUM_ION_TOKEN
```

It is a browser client token, not a backend secret.

## Render Free notes

- Free services are for preview/demo, not production.
- They spin down after inactivity.
- The filesystem is ephemeral at runtime.
- Build-time media inside the Docker image survives normal sleep/restart.
- User-generated Vision artifacts are session/runtime data and can disappear after restart/redeploy.
- Keep demo media compact because outbound bandwidth is limited.

## Acceptance

After deploy, run:

```bash
python scripts/public_smoke.py https://<service>.onrender.com
```

Then manually validate from a phone/other network:

```text
Dashboard
→ 9 events
→ Cesium FlyTo
→ current Sensor
→ NOW/+10/+30
→ current video
→ historical case media
→ Vision upload
→ Water Mask
→ WebSocket
→ Shanghai Water / graceful fallback
```

## Frozen exclusions

Do not add as RC2.4 blockers:
- PostGIS production persistence
- MQTT
- Auth
- real Shanghai LIVE CCTV
- calibrated centimetre-depth model
- production persistence
