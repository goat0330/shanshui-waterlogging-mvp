"""Offline video smoke with an honest missing-source path and optional adapter check."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path

import cv2
import numpy as np

from vision.schema import validate_observation

from .video_pipeline import VideoInputError, run_video_pipeline


ROOT = Path(__file__).resolve().parent
ARTIFACTS = ROOT / "artifacts"
REQUIRED_OUTPUT = ARTIFACTS / "video-smoke.json"
SYNTHETIC_OUTPUT = ARTIFACTS / "video-smoke-synthetic.json"


def _source_required() -> dict[str, object]:
    result: dict[str, object] = {
        "videoId": "VIDEO-SMOKE",
        "status": "VIDEO_SOURCE_REQUIRED",
        "source": {
            "type": "local",
            "value": None,
            "mediaType": "video/mp4",
            "licenseStatus": "NOT_VERIFIED",
        },
        "frames": [],
        "quality": "REJECT",
        "qualityFlags": ["VIDEO_SOURCE_REQUIRED"],
        "model": {
            "framePipeline": "vision.pipeline.run_pipeline",
            "waterSegmentation": "opencv_baseline",
            "referenceDetection": "opencv_hog_and_color_heuristic",
            "geometrySupport": "none",
            "weights": "not_used",
        },
        "synthetic": False,
    }
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    REQUIRED_OUTPUT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result


def _discover_mp4() -> Path | None:
    for path in ROOT.parent.rglob("*.mp4"):
        if any(part in {".git", "node_modules", "__pycache__"} for part in path.parts):
            continue
        return path
    return None


def _resolve(path_value: str) -> Path:
    path = Path(path_value)
    return path if path.is_absolute() else Path.cwd() / path


def _validate_video_result(result: dict[str, object], output_path: Path) -> None:
    assert result["status"] == "COMPLETED", result
    frames = result["frames"]
    assert isinstance(frames, list) and frames, result
    reloaded = json.loads(output_path.read_text(encoding="utf-8"))
    assert reloaded["videoId"] == result["videoId"]
    for frame in frames:
        result_path = _resolve(frame["resultPath"])
        assert result_path.is_file(), result_path
        observation = json.loads(result_path.read_text(encoding="utf-8"))
        validate_observation(observation)
        mask_path = _resolve(observation["waterMaskPath"])
        assert mask_path.is_file(), mask_path
        confidence = observation["depth"]["confidence"]
        assert 0 <= confidence <= 1, observation
        if observation["method"] == "NO_REFERENCE":
            assert observation["depth"]["estimatedDepthCm"] is None, observation
            assert "NO_REFERENCE" in observation["qualityFlags"], observation
        assert frame["overlay"]["waterMaskPath"] == observation["waterMaskPath"]


def _write_synthetic_mp4(path: Path) -> None:
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 8.0, (320, 240))
    if not writer.isOpened():
        writer.release()
        raise RuntimeError("OpenCV MP4 writer is unavailable; synthetic adapter check cannot run")
    try:
        for index in range(6):
            frame = np.full((240, 320, 3), (82, 105, 125), dtype=np.uint8)
            cv2.rectangle(frame, (0, 120), (319, 239), (90, 55, 35), thickness=-1)
            cv2.rectangle(frame, (40 + index * 5, 70), (85 + index * 5, 180), (45, 45, 45), thickness=-1)
            writer.write(frame)
    finally:
        writer.release()


def _run_synthetic_check() -> dict[str, object]:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="vision-video-smoke-") as temp_dir:
        source = Path(temp_dir) / "synthetic-smoke.mp4"
        _write_synthetic_mp4(source)
        result = run_video_pipeline(
            str(source),
            SYNTHETIC_OUTPUT,
            video_id="VIDEO-SMOKE-SYNTHETIC",
            sample_interval_sec=0.25,
            max_frames=3,
            source_license_status="SYNTHETIC_ONLY",
            synthetic=True,
        )
    _validate_video_result(result, SYNTHETIC_OUTPUT)
    assert result["synthetic"] is True
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Smoke the offline VisionDepth video evidence wrapper.")
    parser.add_argument("--input", help="optional local MP4; without it the smoke discovers one if present")
    parser.add_argument(
        "--synthetic-check",
        action="store_true",
        help="also run a clearly labelled temporary synthetic adapter check when no real MP4 is available",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    source = Path(args.input).expanduser() if args.input else _discover_mp4()
    if source is None:
        missing = _source_required()
        print("Video smoke: VIDEO_SOURCE_REQUIRED (no local MP4 found; no CCTV/LIVE result created)")
        print(f"result={REQUIRED_OUTPUT.as_posix()}")
        if not args.synthetic_check:
            return 0
        synthetic = _run_synthetic_check()
        print(
            "synthetic adapter check passed: "
            f"frames={len(synthetic['frames'])} result={SYNTHETIC_OUTPUT.as_posix()}"
        )
        return 0

    try:
        ARTIFACTS.mkdir(parents=True, exist_ok=True)
        result = run_video_pipeline(str(source), REQUIRED_OUTPUT, video_id="VIDEO-SMOKE", max_frames=3)
        _validate_video_result(result, REQUIRED_OUTPUT)
    except VideoInputError as exc:
        print(f"Video smoke input error: {exc}")
        return 2
    print(
        "Video smoke passed: "
        f"frames={len(result['frames'])} result={REQUIRED_OUTPUT.as_posix()} source={source}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
