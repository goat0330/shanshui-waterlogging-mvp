"""One-image VisionDepth V1 pipeline."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from .depth_estimation import estimate_depth
from .ingest import IngestedImage, load_image
from .reference_detection import detect_references
from .schema import validate_observation
from .water_segmentation import segment_water


def _relative_mask_path(mask_path: Path) -> str:
    vision_root = Path(__file__).resolve().parent
    try:
        return mask_path.resolve().relative_to(vision_root.resolve()).as_posix()
    except ValueError:
        return os.path.relpath(mask_path.resolve(), Path.cwd().resolve()).replace("\\", "/")


def _save_mask(mask: np.ndarray, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(mask.astype(np.uint8), mode="L").save(path, format="PNG")


def _quality(segmentation: Any, references: list[Any], flood_detected: bool) -> tuple[str, list[str]]:
    flags = ["BASELINE_ONLY", "MODEL_WEIGHT_MISSING"]
    if not flood_detected:
        flags.append("NO_WATER")
    if not any(reference.reliable for reference in references):
        flags.append("NO_REFERENCE")
    if segmentation.score < 0.32:
        flags.append("WATER_MASK_WEAK")
    return "LOW", flags


def run_pipeline(source: str, output_path: str | Path, image_id: str = "IMG-00001") -> dict[str, Any]:
    ingested: IngestedImage = load_image(source)
    segmentation = segment_water(ingested.rgb)
    references = detect_references(ingested.rgb, segmentation.mask)
    estimate = estimate_depth(segmentation, references)

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    mask_path = output.parent / f"{image_id}-water-mask.png"
    _save_mask(segmentation.mask, mask_path)

    quality, quality_flags = _quality(segmentation, references, estimate["floodDetected"])
    reference_objects = [reference.as_dict() for reference in references]
    observation: dict[str, Any] = {
        "imageId": image_id,
        "source": {"type": ingested.source_type, "value": ingested.source_value},
        "floodDetected": estimate["floodDetected"],
        "depth": {
            "level": estimate["level"],
            "estimatedDepthCm": estimate["estimatedDepthCm"],
            "rangeCm": estimate["rangeCm"],
            "confidence": estimate["confidence"],
        },
        "method": estimate["method"],
        "referenceObjects": reference_objects,
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
