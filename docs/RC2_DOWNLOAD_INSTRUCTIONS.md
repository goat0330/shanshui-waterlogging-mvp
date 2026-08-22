# RC2 research video source and download boundary

This file is a reproducibility note, not a redistribution license.

## Source

The six small MP4 source entries come from the official V-FloodNet `water_videos_for_test` directory on Hugging Face:

<https://huggingface.co/xmlyqing00/V-FloodNet/tree/main/water_videos_for_test>

The public repository records source URLs and SHA-256 values in `docs/RC2_SOURCE_MANIFEST.csv`. It does not contain the MP4 binaries, full dataset, records, Houston 268 MB video or model weights.

## Local-only placement

Place downloaded files outside the Git repository:

```text
D:\研究生作业\上海城市内涝_智慧平台\data\visiondepth\videos\
D:\研究生作业\上海城市内涝_智慧平台\data\visiondepth\manifests\video_manifest.csv
```

The runtime manifest must retain source URL, project, license review state, local-only policy, camera ID, scenario and SHA-256. Use `licenseReview=pending`, `researchMvp=true`, `production=false`, `redistribution=false` until the source terms are independently cleared.

## Run the local research MVP

From `git/backend/visiondepth_v2/`:

```text
python -m tools.data_gate --config configs/local.yaml
python -m tools.video_smoke --config configs/local.yaml
python -m tools.check_third_party --config configs/local.yaml
```

The current evidence is `4 usable videos / 25 sampled frames`. Two source files have 11 frames and are intentionally rejected by the `>=30` frame gate. Do not insert or duplicate frames to make them pass.

## Interpretation limits

- This is a local research MVP, not a public redistribution permission.
- The camera is not calibrated. Every accepted video frame keeps `estimatedDepthCm=null`, `confidence` low and `CAMERA_UNCALIBRATED`.
- The output proves decode/mask/timestamp/overlay plumbing, not calibrated centimetres, accuracy, generalization or a live CCTV feed.
- Do not commit MP4s, model weights, raw datasets or `backend/visiondepth_v2/outputs/` to the public repository.
