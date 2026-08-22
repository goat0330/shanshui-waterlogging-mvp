# VisionDepth offline video evidence

This module accepts a local MP4 only. It samples frames with OpenCV and calls
the existing `vision.pipeline.run_pipeline` for every sampled frame. It does
not parse webpages, download videos, write sensor state, or replace a
FloodPoint value.

```text
python -m media.cli --input path/to/clip.mp4 --output media/artifacts/video-result.json
python -m media.smoke
python -m media.smoke --synthetic-check
python -m compileall vision media
```

Each completed result contains the video source/license status, timestamps,
per-frame JSON and mask paths, the original VisionDepth reference evidence,
coarse level/range, nullable `estimatedDepthCm`, confidence, quality flags,
and metadata-only overlay information. A missing local MP4 produces an
explicit `VIDEO_SOURCE_REQUIRED` smoke artifact; the optional synthetic check
only exercises the adapter and is not real CCTV/LIVE evidence.

The current frame pipeline is the OpenCV V1 baseline. It uses no downloaded
weights and has no geometric support. No external model is upgraded in RC1.1.
