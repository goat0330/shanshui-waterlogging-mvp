# VisionDepth V2 LeanGuard adapter

This package remains the local research/video adapter for the shared `vision.pipeline`. It does not change the `VisionDepthObservation` ownership boundary, write `SensorState`, or overwrite current flood-point depth.

## MVP media gate

The local research-video gate requires a decodable MP4 with at least 30 frames. The six recorded V-FloodNet sample files keep their existing frame-gate evidence: four pass and two 11-frame files are rejected without duplication/interpolation.

For this project:

```text
mvp_use_scope=local_research_only
allowed_in_mvp=true
production=false
redistribution=false
```

External redistribution/production review is a separate gate and must not be treated as a blocker for the local MVP. These videos are never Shanghai LIVE CCTV and must be labeled non-live/research.

## Shared frame engine

Every sampled frame calls `vision.pipeline.run_pipeline`. The pipeline may use the locally configured verified learned water-segmentation checkpoint via `VISION_WATER_SEGMENTATION_CHECKPOINT`; if absent/unloadable it falls back to OpenCV. No second video segmentation algorithm is created here.

Camera calibration remains independent: uncalibrated video keeps metric `estimatedDepthCm` unavailable according to the existing guard. Learned water-mask validation is not centimetre-depth validation.

## Run

```text
python -m pytest -q
python -m tools.data_gate --config configs/local.yaml
python -m tools.video_smoke --config configs/local.yaml
python -m tools.check_third_party --config configs/local.yaml
python -m compileall -q src tools tests
```

Do not commit raw MP4s, model checkpoints, full datasets, `.env.local`, or runtime output bundles.
