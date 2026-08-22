# RC2 Source / Provenance Policy

## Runtime policy

Pending-license research assets may run in the local evidence pipeline:

```text
research_mvp=true
production=false
redistribution=false
```

`licenseReview=pending` is not equivalent to approval. Public GitHub must not contain pending-license MP4 binaries, model weights, full datasets, or runtime outputs.

## Public manifest boundary

The public repository may contain source metadata and reproducible instructions:

```text
assetId, type, sourceUrl, sourceProject, licenseReview,
researchMvp, production, redistribution, localPath, sha256, notes
```

The local manifest may point to `data/visiondepth/**`, but the media remains outside Git. Download instructions must state the expected filenames and the local-only policy.

## UI source truth

Every value shown in the Dashboard must be labeled as one of:

```text
SENSOR        current measured observation
VISION_IMAGE  image evidence estimate
VISION_VIDEO  video/frame evidence estimate
FORECAST      future model or synthetic forecast
```

The current measured sensor value is never overwritten by vision or forecast output. Synthetic, uncalibrated, low-confidence, pending-license and demo/fallback states remain visible where relevant.

## Camera and depth rule

Without a calibrated `CameraProfile`:

```text
estimatedDepthCm = null
CAMERA_UNCALIBRATED
```

The pipeline may still return flood detection, mask, reference evidence, level and range. It must not fabricate centimeter precision.

## Forecast rule

Forecast values remain separate from current measured depth. Current sensor depth and future forecast frames must have independent fields and source labels; fixture forecast is `synthetic=true` until a verified model/data source replaces it.
