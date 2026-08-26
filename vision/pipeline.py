"""One-image VisionDepth pipeline with optional verified learned water mask."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image

from .depth_estimation import estimate_depth
from .ingest import IngestedImage, load_image
from .reference_detection import detect_references
from .schema import validate_observation
from .water_segmentation import WaterSegmentation, segment_water


def _relative_mask_path(mask_path: Path) -> str:
    vision_root = Path(__file__).resolve().parent
    try:
        return mask_path.resolve().relative_to(vision_root.resolve()).as_posix()
    except ValueError:
        return os.path.relpath(mask_path.resolve(), Path.cwd().resolve()).replace("\\", "/")


def _save_mask(mask: np.ndarray, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(mask.astype(np.uint8), mode="L").save(path, format="PNG")


def _largest_component_fraction(mask: np.ndarray) -> float:
    binary = (mask > 0).astype(np.uint8)
    count, _, stats, _ = cv2.connectedComponentsWithStats(binary, 8)
    if count <= 1:
        return 0.0
    largest = max(int(stats[index, cv2.CC_STAT_AREA]) for index in range(1, count))
    return float(largest / max(mask.shape[0] * mask.shape[1], 1))


def _checkpoint_path() -> Path | None:
    configured = os.getenv("VISION_WATER_SEGMENTATION_CHECKPOINT", "").strip()
    if configured:
        candidate = Path(configured).expanduser()
        return candidate if candidate.is_file() else None

    repo_root = Path(__file__).resolve().parents[1]
    relative = Path("data/visiondepth/research/Urban-Flood-Image-Dataset/candidate-water-segmentation.joblib")
    for candidate in (repo_root / relative, repo_root.parent / relative):
        if candidate.is_file():
            return candidate
    return None


def _segment(image_rgb: np.ndarray) -> WaterSegmentation:
    baseline = segment_water(image_rgb)
    checkpoint = _checkpoint_path()
    if checkpoint is None:
        return baseline

    try:
        from .learned_segmentation import predict_water_mask
        learned = predict_water_mask(image_rgb, checkpoint)
    except Exception:
        # A local optional checkpoint must never make the MVP image/video path
        # unavailable. The baseline remains the deterministic fallback.
        return baseline

    # Preserve the existing baseline dry-scene guard. The learned candidate is
    # verified for water-mask research evidence, not domain-wide dry-scene
    # classification, so it must not override a clear baseline no-water signal.
    if (
        baseline.score < 0.22
        or baseline.largest_component_fraction == 0
        or baseline.water_color_fraction < 0.70
        or baseline.lower_red_blue_contrast < 10.0
    ):
        return baseline

    mask = learned.mask.astype(np.uint8)
    height = mask.shape[0]
    water_fraction = float(np.mean(mask > 0))
    lower_fraction = float(np.mean(mask[int(height * 0.55):] > 0)) if height else 0.0
    largest_fraction = _largest_component_fraction(mask)
    extent_score = min(1.0, largest_fraction / 0.20)
    lower_score = min(1.0, lower_fraction / 0.60)
    # This is only a visual range score used by the existing coarse-level path;
    # it is not a calibrated centimetre prediction.
    score = float(np.clip(0.45 * learned.mean_probability + 0.30 * extent_score + 0.25 * lower_score, 0.0, 1.0))
    return WaterSegmentation(
        mask=mask,
        score=score,
        water_fraction=water_fraction,
        lower_fraction=lower_fraction,
        largest_component_fraction=largest_fraction,
        water_color_fraction=baseline.water_color_fraction,
        lower_red_blue_contrast=baseline.lower_red_blue_contrast,
        roughness=baseline.roughness,
        method=learned.method,
    )


def _quality(segmentation: Any, references: list[Any], flood_detected: bool, approximate_depth_cm: float | None = None) -> tuple[str, list[str]]:
    learned = segmentation.method == "pixel_logistic_regression"
    flags = ["LEARNED_WATER_SEGMENTATION", "METRIC_DEPTH_UNVERIFIED"] if learned else ["BASELINE_ONLY", "MODEL_WEIGHT_MISSING"]
    if not flood_detected:
        flags.append("NO_WATER")
    if not any(reference.reliable for reference in references):
        flags.append("NO_REFERENCE")
    if segmentation.score < 0.32:
        flags.append("WATER_MASK_WEAK")
    if approximate_depth_cm is not None:
        flags.append("ROUGH_VISUAL_ESTIMATE")
    return "LOW", flags


def run_pipeline(source: str, output_path: str | Path, image_id: str = "IMG-00001") -> dict[str, Any]:
    ingested: IngestedImage = load_image(source)
    segmentation = _segment(ingested.rgb)
    references = detect_references(ingested.rgb, segmentation.mask)
    estimate = estimate_depth(segmentation, references)

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    mask_path = output.parent / f"{image_id}-water-mask.png"
    _save_mask(segmentation.mask, mask_path)

    quality, quality_flags = _quality(segmentation, references, estimate["floodDetected"], estimate["approximateDepthCm"])
    observation: dict[str, Any] = {
        "imageId": image_id,
        "source": {"type": ingested.source_type, "value": ingested.source_value},
        "floodDetected": estimate["floodDetected"],
        "depth": {
            "level": estimate["level"],
            "estimatedDepthCm": estimate["estimatedDepthCm"],
            "approximateDepthCm": estimate["approximateDepthCm"],
            "rangeCm": estimate["rangeCm"],
            "confidence": estimate["confidence"],
        },
        "method": estimate["method"],
        "referenceObjects": [reference.as_dict() for reference in references],
        "waterMaskPath": _relative_mask_path(mask_path),
        "quality": quality,
        "qualityFlags": quality_flags,
        "model": {
            "waterSegmentation": segmentation.method,
            "referenceDetection": "opencv_hog_and_color_heuristic",
            "geometrySupport": "none",
        },
        "synthetic": False,
    }
    validate_observation(observation)
    output.write_text(json.dumps(observation, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return observation
