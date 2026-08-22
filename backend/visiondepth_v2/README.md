# VisionDepth V2 LeanGuard adapter

This package is an isolated research/data gate for the existing VisionDepth
V1 evidence pipeline. It does not replace the fixed
`VisionDepthObservation` contract, change FastAPI routes, write SensorState,
or overwrite `FloodPoint.currentDepthCm`.

## Current execution boundary

The first gate is an authorized local MP4. The manifest must record its source,
license, authorization, camera and scenario. The gate requires a decodable MP4
with at least 30 frames. If no such source exists, the result is explicitly
`VIDEO_SOURCE_REQUIRED`; no synthetic or CCTV/LIVE result is manufactured.

The frame engine calls the existing `vision.pipeline.run_pipeline`. V2 adds
only a camera-calibration guard: when the camera is uncalibrated,
`estimatedDepthCm` is forced to `null` and confidence is capped low. Water
segmentation and reference detection are not duplicated here.

V-FloodNet remains an external research adapter only. Its source, weights and
large datasets are not copied or committed. The six small test videos are
kept outside Git for this local-only MVP smoke and are recorded as
`MVP_REVIEW`; this is not final public-use approval. The registry keeps the
pending license state. `tools.check_third_party --config configs/local.yaml`
passes only for the explicitly non-redistributable `research_mvp` profile and
still blocks production, redistribution and external model execution.

## Run from this directory

```text
python -m pytest -q
python -m tools.data_gate --config configs/local.yaml
python -m tools.video_smoke --config configs/local.yaml
python -m tools.check_third_party --config configs/local.yaml
python -m tools.eval_masks --pred outputs/masks --gt ../../../../data/visiondepth/gt_masks
python -m compileall -q src tools tests
```

The data and third-party roots are intentionally outside Git. Do not add MP4,
model weights, raw datasets, `.env.local`, or external repositories to this
package. `runtime_profile: research_mvp` permits only the local OpenCV path;
it does not approve pending third-party licenses, external model execution, or
redistribution. Production/redistribution profiles remain blocked until review
is explicitly approved.
