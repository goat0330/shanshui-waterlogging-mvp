# RC2 research video source and local-use boundary

The six small MP4 entries come from V-FloodNet `water_videos_for_test` and are recorded by URL/SHA-256 in `docs/RC2_SOURCE_MANIFEST.csv`. MP4 binaries, full datasets and model weights stay outside public Git.

## Project gate

```text
mvpUseStatus=APPROVED_LOCAL_RESEARCH
researchMvp=true
production=false
redistribution=false
licenseReview=pending_external_redistribution
```

`pending_external_redistribution` is **not** an MVP blocker. It means the project does not claim blanket public redistribution or production permission.

## Run

From `backend/visiondepth_v2/`:

```text
python -m tools.data_gate --config configs/local.yaml
python -m tools.video_smoke --config configs/local.yaml
python -m tools.check_third_party --config configs/local.yaml
```

Current frame gate evidence remains `4 usable videos / 25 sampled frames`; the two 11-frame clips remain rejected without duplication/interpolation.

## Display boundary

- label the media **non-live / research video**;
- never label it Shanghai LIVE CCTV;
- uncalibrated camera evidence is not production centimetre depth;
- do not commit raw MP4s, external checkpoints, full datasets, or runtime outputs.
