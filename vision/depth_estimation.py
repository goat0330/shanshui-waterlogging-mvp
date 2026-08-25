"""Coarse, fixed-level depth reasoning from mask and reference evidence."""

from __future__ import annotations

from typing import Any

from .reference_detection import ReferenceEvidence
from .schema import clamp, level_for_depth, range_for_level
from .water_segmentation import WaterSegmentation


def _visual_level(segmentation: WaterSegmentation) -> int:
    if segmentation.score < 0.32:
        return 1
    if segmentation.score < 0.46:
        return 2
    if segmentation.score < 0.62:
        return 3
    if segmentation.score < 0.80:
        return 4
    return 5


def _approximate_depth(level: int) -> float | None:
    """Return a coarse display value for the visual range, never a metric estimate."""

    minimum, maximum = range_for_level(level)
    if minimum is None:
        return None
    if maximum is None:
        return None
    return round((minimum + maximum) / 2.0, 1)


def _reference_depth(reference: ReferenceEvidence, image_height: int) -> float | None:
    if not reference.reliable or reference.waterline_y is None:
        return None
    _, y, _, height = reference.bbox
    bottom = y + height
    waterline_px = reference.waterline_y * max(1, image_height - 1)
    # The HOG/color box is a perspective cue, not a metric measurement. A full
    # reference height prior is intentionally used only to produce a coarse bin.
    top_norm = y / max(image_height - 1, 1)
    bottom_norm = bottom / max(image_height - 1, 1)
    if top_norm <= reference.waterline_y <= bottom_norm:
        visible_submersion = (bottom - waterline_px) / max(height, 1)
    else:
        # If the local mask overlaps a small, distant reference but its global
        # waterline misses the box, retain only a coarse overlap-based cue.
        visible_submersion = min(0.30, reference.water_overlap_ratio)
    if visible_submersion <= 0.04:
        return None
    prior_cm = {
        "PERSON_REFERENCE": 170.0,
        "VEHICLE_REFERENCE": 150.0,
        "TRAFFIC_SIGN_REFERENCE": 180.0,
        "FIXED_CAMERA_REFERENCE": 200.0,
    }.get(reference.type)
    if prior_cm is None:
        return None
    return max(1.0, min(150.0, prior_cm * visible_submersion))


def estimate_depth(
    segmentation: WaterSegmentation,
    references: list[ReferenceEvidence],
) -> dict[str, Any]:
    reliable = [reference for reference in references if reference.reliable]
    reliable.sort(key=lambda reference: (reference.confidence, reference.water_overlap_ratio), reverse=True)
    reference = reliable[0] if reliable else None

    if (
        segmentation.score < 0.22
        or segmentation.largest_component_fraction == 0
        or segmentation.water_color_fraction < 0.70
        or segmentation.lower_red_blue_contrast < 10.0
    ):
        return {
            "floodDetected": False,
            "level": 0,
            "estimatedDepthCm": None,
            "approximateDepthCm": None,
            "rangeCm": range_for_level(0),
            "confidence": round(clamp(0.42 + (0.22 - segmentation.score) * 0.2, 0.25, 0.6), 3),
            "method": "VISUAL_RANGE",
            "reference": None,
        }

    if reference:
        estimated = _reference_depth(reference, segmentation.mask.shape[0])
        if estimated is not None:
            level = level_for_depth(estimated)
            confidence = clamp(0.18 + 0.18 * reference.confidence + 0.12 * segmentation.score, 0.25, 0.48)
            return {
                "floodDetected": True,
                "level": level,
                "estimatedDepthCm": round(estimated, 1),
                "approximateDepthCm": None,
                "rangeCm": range_for_level(level),
                "confidence": round(confidence, 3),
                "method": reference.type,
                "reference": reference,
            }

    level = _visual_level(segmentation)
    confidence = clamp(0.18 + 0.28 * segmentation.score, 0.20, 0.40)
    return {
        "floodDetected": True,
        "level": level,
        "estimatedDepthCm": None,
        "approximateDepthCm": _approximate_depth(level),
        "rangeCm": range_for_level(level),
        "confidence": round(confidence, 3),
        "method": "NO_REFERENCE",
        "reference": None,
    }
