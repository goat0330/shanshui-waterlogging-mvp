"""Offline MP4 sampler that reuses the one-image VisionDepth V1 pipeline."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import cv2

from vision.pipeline import run_pipeline
from vision.schema import validate_observation


MAX_VIDEO_BYTES = 512 * 1024 * 1024


class VideoInputError(ValueError):
    """Raised when a local MP4 cannot be used as an offline evidence source."""


def _relative_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return os.path.relpath(path.resolve(), Path.cwd().resolve()).replace("\\", "/")


def _validate_video_id(video_id: str) -> str:
    if not video_id or Path(video_id).name != video_id or video_id in {".", ".."}:
        raise ValueError("video_id must be a simple file-safe identifier")
    return video_id


def _local_mp4(source: str) -> Path:
    path = Path(source).expanduser()
    if not path.is_file():
        raise VideoInputError(f"local MP4 does not exist: {source}")
    if path.suffix.lower() != ".mp4":
        raise VideoInputError(f"video input must be an MP4 file: {source}")
    if path.stat().st_size <= 0:
        raise VideoInputError(f"video file is empty: {source}")
    if path.stat().st_size > MAX_VIDEO_BYTES:
        raise VideoInputError(f"video exceeds {MAX_VIDEO_BYTES // (1024 * 1024)} MB limit: {source}")
    return path


def _overlay_metadata(
    observation: dict[str, Any], frame_path: Path, result_path: Path
) -> dict[str, Any]:
    references = observation["referenceObjects"]
    return {
        "status": "METADATA_ONLY",
        "rendered": False,
        "framePath": _relative_path(frame_path),
        "resultPath": _relative_path(result_path),
        "waterMaskPath": observation["waterMaskPath"],
        "referenceEvidenceCount": len(references),
        "reliableReferenceCount": sum(bool(item.get("reliable")) for item in references),
        "referenceBoxes": [item["bbox"] for item in references],
        "floodDetected": observation["floodDetected"],
        "level": observation["depth"]["level"],
        "method": observation["method"],
    }


def _write_frame(frame: Any, path: Path) -> None:
    encoded_ok, encoded = cv2.imencode(".png", frame, [cv2.IMWRITE_PNG_COMPRESSION, 3])
    if not encoded_ok:
        raise OSError(f"could not encode sampled frame: {path}")
    path.write_bytes(encoded.tobytes())


def run_video_pipeline(
    source: str,
    output_path: str | Path,
    video_id: str = "VID-00001",
    sample_interval_sec: float = 1.0,
    max_frames: int = 60,
    source_license_status: str = "NOT_VERIFIED",
    synthetic: bool = False,
) -> dict[str, Any]:
    """Sample a local MP4 and run VisionDepth V1 once per sampled frame.

    The video layer owns sampling and evidence packaging only. Water masks,
    reference detection, and depth reasoning stay in ``vision.pipeline``.
    """

    if sample_interval_sec <= 0:
        raise ValueError("sample_interval_sec must be greater than zero")
    if max_frames <= 0:
        raise ValueError("max_frames must be greater than zero")
    video_id = _validate_video_id(video_id)
    video_path = _local_mp4(source)
    license_status = str(source_license_status).strip() or "NOT_VERIFIED"

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    frame_dir = output.parent / f"{video_id}-frames"
    frame_dir.mkdir(parents=True, exist_ok=True)

    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        capture.release()
        raise VideoInputError(f"OpenCV could not open MP4: {source}")

    raw_fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
    fps = raw_fps if raw_fps > 0 else 0.0
    declared_frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    stride = max(1, round(fps * sample_interval_sec)) if fps else 1
    frames: list[dict[str, Any]] = []
    frame_index = 0

    try:
        while len(frames) < max_frames:
            ok, frame = capture.read()
            if not ok:
                break
            if frame_index % stride == 0:
                frame_id = f"{video_id}-F{frame_index:06d}"
                frame_path = frame_dir / f"{frame_id}.png"
                _write_frame(frame, frame_path)
                frame_result_path = output.parent / f"{frame_id}.json"
                observation = run_pipeline(str(frame_path), frame_result_path, frame_id)
                validate_observation(observation)
                timestamp_sec = frame_index / fps if fps else float(frame_index)
                frames.append(
                    {
                        "frameIndex": frame_index,
                        "timestampMs": round(timestamp_sec * 1000.0, 3),
                        "timestampSec": round(timestamp_sec, 3),
                        "framePath": _relative_path(frame_path),
                        "resultPath": _relative_path(frame_result_path),
                        "observation": observation,
                        "overlay": _overlay_metadata(observation, frame_path, frame_result_path),
                    }
                )
            frame_index += 1
    finally:
        capture.release()

    if not frames:
        raise VideoInputError(f"MP4 contains no readable frames: {source}")

    quality_flags = ["BASELINE_ONLY", "MODEL_WEIGHT_MISSING", "OVERLAY_METADATA_ONLY"]
    if license_status != "VERIFIED":
        quality_flags.append("LICENSE_NOT_VERIFIED")
    if synthetic:
        quality_flags.append("SYNTHETIC_INPUT")

    result: dict[str, Any] = {
        "videoId": video_id,
        "status": "COMPLETED",
        "source": {
            "type": "local",
            "value": source,
            "mediaType": "video/mp4",
            "licenseStatus": license_status,
        },
        "video": {
            "width": width,
            "height": height,
            "fps": round(fps, 3),
            "frameCount": declared_frame_count,
            "decodedFrameCount": frame_index,
            "durationSec": round(declared_frame_count / fps, 3) if fps and declared_frame_count else None,
            "sampleIntervalSec": sample_interval_sec,
            "sampleStrideFrames": stride,
            "sampledFrameCount": len(frames),
            "timestampUnit": "milliseconds",
            "sampler": "opencv_video_capture_sequential_stride",
        },
        "frames": frames,
        "quality": "LOW",
        "qualityFlags": quality_flags,
        "model": {
            "framePipeline": "vision.pipeline.run_pipeline",
            "waterSegmentation": "opencv_baseline",
            "referenceDetection": "opencv_hog_and_color_heuristic",
            "geometrySupport": "none",
            "weights": "not_used",
            "licenseStatus": "no_external_model_weights",
        },
        "synthetic": synthetic,
    }
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return result
