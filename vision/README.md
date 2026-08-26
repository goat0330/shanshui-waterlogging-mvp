# VisionDepth — MVP runtime

The shared image/video path now supports an optional learned water-segmentation checkpoint while preserving the OpenCV fallback.

## Default

The runtime first checks `VISION_WATER_SEGMENTATION_CHECKPOINT`, then the project-local/sibling `data/visiondepth/research/Urban-Flood-Image-Dataset/candidate-water-segmentation.joblib`. If no valid checkpoint exists, the existing OpenCV baseline runs unchanged.

## Learned mask path

The checked-in candidate has held-out WebCOOS mask evidence:

```text
pixel_logistic_regression IoU = 0.648314
OpenCV baseline IoU          = 0.395276
```

To use the local checkpoint:

```powershell
$env:VISION_WATER_SEGMENTATION_CHECKPOINT = "D:\path\candidate-water-segmentation.joblib"
```

The pipeline loads a valid checkpoint once per process and reuses it across image/video frames; otherwise it falls back to OpenCV. No weights are downloaded and no checkpoint is committed.

This changes the water mask/evidence path only. It does **not** make the system a calibrated centimetre-depth model. `estimatedDepthCm` and camera-calibration guards remain governed by the existing evidence rules.

The video pipeline reuses the same `vision.pipeline`, so the same optional learned mask path applies to sampled video frames without creating a second video algorithm.
