# VisionDepth V1

`VisionDepth V1` turns one local JPEG/PNG/WebP image or one HTTP/HTTPS image URL into an independent flood-depth evidence JSON. It does not parse webpages, write sensor state, replace `FloodPoint.currentDepthCm`, or provide a production inference service.

## Run

From the repository root:

```text
python -m vision.cli --input path/to/image.jpg --output vision/artifacts/result.json --save-mask
python -m vision.cli --input https://example.org/image.jpg --output vision/artifacts/result.json
python -m vision.smoke
python -m compileall vision
```

The mask is saved beside the JSON in V1 even without `--save-mask`; the flag is retained as an explicit command-line affordance. The output always uses the fixed levels:

```text
0: no obvious flood
1: 0-10 cm
2: 10-20 cm
3: 20-30 cm
4: 30-50 cm
5: >50 cm
```

## Method boundary

The current implementation is an OpenCV baseline:

- water mask: HSV/color exclusion, lower-scene prior, gradient/texture and connected components;
- reference evidence: OpenCV built-in HOG people detector and a conservative red/orange compact-blob candidate for traffic signs;
- geometry: `none`; no Depth Anything model and no monocular-to-centimeter claim;
- no downloaded model weights are required or assumed.

The smoke-calibrated baseline requires a lower-scene brown/blue chroma cue (`R-B` contrast) before declaring obvious water. It is intentionally conservative against dry pavement and can miss neutral-gray or night-time water; this is a known V1 ceiling, not a production accuracy claim.

An object box alone never produces a depth estimate. A centimeter estimate is emitted only when the reference evidence overlaps the water candidate and a waterline cue is available. Otherwise `estimatedDepthCm` is `null`, the method is `NO_REFERENCE`, and confidence is capped low.

The V-FloodNet project was used only as an architecture reference (water segmentation -> reference object -> waterline/submersion -> coarse depth). Its source was not copied; the repository planning document records its license metadata as undeclared, so it is not a runtime dependency.

## Runtime dependencies

The verified environment already contains Python 3.11, OpenCV 4.13, Pillow 11.3, NumPy 1.26 and requests 2.32. No new package was installed for V1. `torch`, `transformers` and `ultralytics` may exist in the environment but are intentionally not used without verified weights and a separate license decision.

## URL safety

Only HTTP/HTTPS URLs are accepted. Requests use connect/read timeouts, redirects are revalidated, content type and decoded image format must be JPEG/PNG/WebP, and the response is limited to 15 MB and 20 megapixels. A failed download or webpage response exits non-zero; it never emits a fabricated observation.
