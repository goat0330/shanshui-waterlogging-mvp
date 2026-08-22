"""Find authorized, decodable local MP4 evidence without downloading data."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any

import cv2
import yaml


PACKAGE_ROOT = Path(__file__).resolve().parents[1]


def load_config(config_path: str | Path) -> tuple[Path, dict[str, Any]]:
    path = Path(config_path).resolve()
    value = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(value, dict):
        raise ValueError("config must be a YAML object")
    return path, value


def _resolve_config_path(config_path: Path, value: str) -> Path:
    candidate = Path(value).expanduser()
    return (config_path.parent / candidate).resolve() if not candidate.is_absolute() else candidate.resolve()


def manifest_path(config_path: str | Path, config: dict[str, Any]) -> Path:
    path = Path(config_path).resolve()
    configured_root = _resolve_config_path(path, config.get("paths", {}).get("data_root", "data"))
    data_root = configured_root
    if not configured_root.exists():
        # The same package runs from git/ and from an isolated worktree. Keep
        # runtime data at the project root without hard-coding a user path.
        for parent in path.parents:
            candidate = parent / "data" / "visiondepth"
            if candidate.is_dir():
                data_root = candidate
                break
    return data_root / "manifests" / "video_manifest.csv"


def _is_true(value: str | bool | None) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y", "approved"}


def _probe(path: Path) -> dict[str, int | float] | None:
    capture = cv2.VideoCapture(str(path))
    try:
        if not capture.isOpened():
            return None
        fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
        frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        if frame_count < 30 or width <= 0 or height <= 0:
            return None
        return {"fps": fps, "frameCount": frame_count, "width": width, "height": height}
    finally:
        capture.release()


def find_usable_videos(config_path: str | Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    path, config = load_config(config_path)
    manifest = manifest_path(path, config)
    if not manifest.is_file():
        return config, []

    usable: list[dict[str, Any]] = []
    with manifest.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            source = Path(row.get("path", "")).expanduser()
            if not source.is_absolute():
                source = (manifest.parent / source).resolve()
            if not _is_true(row.get("authorized")) or source.suffix.lower() != ".mp4":
                continue
            license_status = str(row.get("license", "")).strip()
            if not license_status or license_status.upper() in {"REVIEW_REQUIRED", "UNKNOWN", "UNVERIFIED"}:
                continue
            if not source.is_file():
                continue
            probe = _probe(source)
            if probe is None:
                continue
            usable.append(
                {
                    "videoId": row.get("video_id") or source.stem,
                    "path": str(source),
                    "sourceUrl": row.get("source_url", ""),
                    "license": license_status,
                    "cameraId": row.get("camera_id", ""),
                    "scenario": row.get("scenario", ""),
                    **probe,
                }
            )
    return config, usable


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(PACKAGE_ROOT / "configs" / "local.yaml"))
    args = parser.parse_args()
    config_path = Path(args.config)
    config, usable = find_usable_videos(config_path)
    manifest = manifest_path(config_path, config)
    if not manifest.is_file():
        print(f"VIDEO_SOURCE_REQUIRED: missing manifest {manifest}")
        return 2
    if not usable:
        print("VIDEO_SOURCE_REQUIRED: no authorized, licensed, decodable local MP4 with >=30 frames")
        return 3
    print(f"DATA_GATE_PASS: {len(usable)} usable video(s)")
    for item in usable:
        print(f"- {item['videoId']}: {item['path']} ({item['frameCount']} frames)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
