"""Run the offline MP4 evidence smoke without inventing a missing source."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PACKAGE_ROOT.parents[1]
for import_root in (PACKAGE_ROOT, REPO_ROOT):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

from media.video_pipeline import run_video_pipeline  # noqa: E402
from src.visiondepth.engine import guard_observation, is_calibrated  # noqa: E402
from tools.data_gate import find_usable_videos, load_config, manifest_path  # noqa: E402


def _resolve_path(value: str | Path) -> Path:
    path = Path(value)
    if path.is_absolute():
        return path
    candidates = [Path.cwd() / path, PACKAGE_ROOT / path, REPO_ROOT / path]
    return next((candidate.resolve() for candidate in candidates if candidate.exists()), candidates[0].resolve())


def _load_camera_profile(config: dict[str, Any]) -> dict[str, Any] | None:
    profile_value = config.get("camera_profile")
    if not profile_value:
        return None
    profile_path = _resolve_path(profile_value)
    value = yaml_safe_load(profile_path)
    return value if isinstance(value, dict) else None


def yaml_safe_load(path: Path) -> Any:
    import yaml

    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _output_root(config_path: Path, config: dict[str, Any]) -> Path:
    configured = str(config.get("paths", {}).get("output_root", "outputs"))
    value = Path(configured).expanduser()
    return (config_path.parent / value).resolve() if not value.is_absolute() else value.resolve()


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _guard_video_result(
    result: dict[str, Any],
    camera_profile: dict[str, Any] | None,
    allow_uncalibrated_depth_cm: bool,
) -> dict[str, Any]:
    for frame in result["frames"]:
        observation = guard_observation(
            frame["observation"],
            camera_profile=camera_profile,
            allow_uncalibrated_depth_cm=allow_uncalibrated_depth_cm,
        )
        frame["observation"] = observation
        result_path = _resolve_path(frame["resultPath"])
        _write_json(result_path, observation)
        frame["overlay"].update(
            {
                "floodDetected": observation["floodDetected"],
                "level": observation["depth"]["level"],
                "method": observation["method"],
                "estimatedDepthCm": observation["depth"]["estimatedDepthCm"],
                "confidence": observation["depth"]["confidence"],
                "quality": observation["quality"],
                "qualityFlags": observation["qualityFlags"],
            }
        )
    result["quality"] = "LOW"
    flags = set(result.get("qualityFlags", []))
    if not is_calibrated(camera_profile) and not allow_uncalibrated_depth_cm:
        flags.add("CAMERA_UNCALIBRATED")
    result["qualityFlags"] = sorted(flags)
    result["calibrationStatus"] = (
        camera_profile.get("calibrationStatus", "unknown") if camera_profile else "missing"
    )
    result["synthetic"] = False
    return result


def _frame_summary(frame: dict[str, Any]) -> dict[str, Any]:
    observation = frame["observation"]
    return {
        "frameId": observation["imageId"],
        "timestampMs": frame["timestampMs"],
        "resultPath": frame["resultPath"],
        "waterMaskPath": observation["waterMaskPath"],
        "floodDetected": observation["floodDetected"],
        "level": observation["depth"]["level"],
        "rangeCm": observation["depth"]["rangeCm"],
        "estimatedDepthCm": observation["depth"]["estimatedDepthCm"],
        "confidence": observation["depth"]["confidence"],
        "method": observation["method"],
        "quality": observation["quality"],
        "qualityFlags": observation["qualityFlags"],
        "overlay": frame["overlay"],
    }


def run(config_path: str | Path) -> tuple[int, dict[str, Any]]:
    config_path, config = load_config(config_path)
    output_root = _output_root(config_path, config)
    camera_profile = _load_camera_profile(config)
    allow_uncalibrated = bool(config.get("guard", {}).get("allow_uncalibrated_depth_cm", False))
    _, usable = find_usable_videos(config_path)
    if not usable:
        summary = {
            "status": "VIDEO_SOURCE_REQUIRED",
            "reason": "No authorized, licensed, decodable local MP4 with >=30 frames was found.",
            "manifest": str(manifest_path(config_path, config)),
            "sampledFrames": 0,
            "frames": [],
            "synthetic": False,
            "notVerified": ["real_video_evidence", "per_frame_inference"],
        }
        _write_json(output_root / "smoke" / "VIDEO_SOURCE_REQUIRED" / "smoke_summary.json", summary)
        return 2, summary

    video = usable[0]
    every = max(1, int(config.get("video", {}).get("sample_every_n_frames", 15)))
    fps = float(video["fps"] or 0.0)
    available_stride = max(1, (int(video["frameCount"]) - 1) // 2)
    stride = min(every, available_stride)
    interval = stride / fps if fps else 1.0
    max_samples = max(3, int(config.get("video", {}).get("max_samples", 12)))
    result_path = output_root / "smoke" / str(video["videoId"]) / "video-result.json"
    result = run_video_pipeline(
        video["path"],
        result_path,
        video_id=str(video["videoId"]),
        sample_interval_sec=interval,
        max_frames=max_samples,
        source_license_status=str(video["license"]),
        synthetic=False,
    )
    result = _guard_video_result(result, camera_profile, allow_uncalibrated)
    _write_json(result_path, result)
    summary = {
        "status": "PASS" if len(result["frames"]) >= 3 else "VIDEO_SMOKE_INSUFFICIENT_FRAMES",
        "videoId": result["videoId"],
        "source": result["source"],
        "sampledFrames": len(result["frames"]),
        "frames": [_frame_summary(frame) for frame in result["frames"]],
        "resultPath": str(result_path),
        "synthetic": False,
        "calibrationStatus": result["calibrationStatus"],
        "qualityFlags": result["qualityFlags"],
    }
    _write_json(result_path.parent / "smoke_summary.json", summary)
    return (0 if summary["status"] == "PASS" else 5), summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(PACKAGE_ROOT / "configs" / "local.yaml"))
    args = parser.parse_args()
    code, summary = run(args.config)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
