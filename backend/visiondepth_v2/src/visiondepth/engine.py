from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[4]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from vision.pipeline import run_pipeline  # noqa: E402
from vision.schema import validate_observation  # noqa: E402


def is_calibrated(camera_profile: dict[str, Any] | None) -> bool:
    return bool(camera_profile and camera_profile.get("calibrationStatus") == "calibrated")


def guard_observation(
    observation: dict[str, Any],
    camera_profile: dict[str, Any] | None = None,
    allow_uncalibrated_depth_cm: bool = False,
) -> dict[str, Any]:
    """Apply the V2 safety guard without adding a second depth algorithm."""

    guarded = copy.deepcopy(observation)
    if not is_calibrated(camera_profile) and not allow_uncalibrated_depth_cm:
        guarded["depth"]["estimatedDepthCm"] = None
        guarded["depth"]["confidence"] = min(float(guarded["depth"]["confidence"]), 0.45)
        guarded["quality"] = "LOW"
        flags = set(guarded.get("qualityFlags", []))
        flags.add("CAMERA_UNCALIBRATED")
        guarded["qualityFlags"] = sorted(flags)
        model = dict(guarded.get("model", {}))
        model["geometrySupport"] = "none"
        guarded["model"] = model
    validate_observation(guarded)
    return guarded


class VisionDepthEngine:
    """V2 boundary over the existing root VisionDepth pipeline."""

    def __init__(
        self,
        camera_profile: dict[str, Any] | None = None,
        allow_uncalibrated_depth_cm: bool = False,
    ) -> None:
        self.camera_profile = camera_profile
        self.allow_uncalibrated_depth_cm = allow_uncalibrated_depth_cm

    def infer_image(
        self, source: str, output_path: str | Path, image_id: str
    ) -> dict[str, Any]:
        observation = run_pipeline(source, output_path, image_id=image_id)
        guarded = guard_observation(
            observation,
            camera_profile=self.camera_profile,
            allow_uncalibrated_depth_cm=self.allow_uncalibrated_depth_cm,
        )
        Path(output_path).write_text(
            json.dumps(guarded, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return guarded

