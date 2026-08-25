"""Stable JSON schema helpers for VisionDepth observations."""

from __future__ import annotations

from typing import Any


LEVEL_RANGES: dict[int, tuple[int, int | None]] = {
    0: (0, 0),
    1: (0, 10),
    2: (10, 20),
    3: (20, 30),
    4: (30, 50),
    5: (50, None),
}

METHODS = {
    "VISUAL_RANGE",
    "NO_REFERENCE",
    "PERSON_REFERENCE",
    "VEHICLE_REFERENCE",
    "TRAFFIC_SIGN_REFERENCE",
    "FIXED_CAMERA_REFERENCE",
}


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, float(value)))


def level_for_depth(depth_cm: float | None) -> int:
    if depth_cm is None or depth_cm <= 0:
        return 0
    if depth_cm < 10:
        return 1
    if depth_cm < 20:
        return 2
    if depth_cm < 30:
        return 3
    if depth_cm < 50:
        return 4
    return 5


def range_for_level(level: int) -> list[int | None]:
    if level not in LEVEL_RANGES:
        raise ValueError(f"unsupported depth level: {level}")
    return list(LEVEL_RANGES[level])


def validate_observation(observation: dict[str, Any]) -> dict[str, Any]:
    """Validate the required shape without coupling it to backend contracts."""

    required = {
        "imageId",
        "source",
        "floodDetected",
        "depth",
        "method",
        "referenceObjects",
        "waterMaskPath",
        "quality",
        "qualityFlags",
        "model",
        "synthetic",
    }
    missing = required - observation.keys()
    if missing:
        raise ValueError(f"observation missing keys: {sorted(missing)}")

    source = observation["source"]
    if source.get("type") not in {"url", "local"} or not source.get("value"):
        raise ValueError("source must contain type=url|local and a value")

    depth = observation["depth"]
    if depth["level"] not in LEVEL_RANGES:
        raise ValueError("depth.level must be 0..5")
    if depth["estimatedDepthCm"] is not None and depth["estimatedDepthCm"] < 0:
        raise ValueError("estimatedDepthCm must be non-negative or null")
    approximate = depth.get("approximateDepthCm")
    if approximate is not None and approximate < 0:
        raise ValueError("approximateDepthCm must be non-negative or null")
    if depth["estimatedDepthCm"] is not None and approximate is not None:
        raise ValueError("estimatedDepthCm and approximateDepthCm cannot both be set")
    if approximate is not None:
        minimum, maximum = LEVEL_RANGES[depth["level"]]
        if maximum is None or minimum is None or depth["level"] == 0:
            raise ValueError("approximateDepthCm requires a finite non-zero visual range")
        expected = (minimum + maximum) / 2.0
        if round(float(approximate), 1) != round(expected, 1):
            raise ValueError("approximateDepthCm must be the midpoint of its visual range")
    if len(depth["rangeCm"]) != 2:
        raise ValueError("depth.rangeCm must contain two values")
    if not 0 <= float(depth["confidence"]) <= 1:
        raise ValueError("depth.confidence must be in [0, 1]")
    method = observation["method"]
    if method not in METHODS:
        raise ValueError(f"unsupported method: {observation['method']}")
    if method == "NO_REFERENCE" and depth["estimatedDepthCm"] is not None:
        raise ValueError("NO_REFERENCE observations cannot emit estimatedDepthCm")
    if method == "NO_REFERENCE" and "NO_REFERENCE" not in observation["qualityFlags"]:
        raise ValueError("NO_REFERENCE observations must carry the NO_REFERENCE quality flag")
    if not observation["floodDetected"] and depth["level"] != 0:
        raise ValueError("non-flood observations must use level 0")
    if observation["quality"] not in {"LOW", "MEDIUM", "HIGH", "REJECT"}:
        raise ValueError("quality must be LOW|MEDIUM|HIGH|REJECT")
    if not isinstance(observation["referenceObjects"], list):
        raise ValueError("referenceObjects must be a list")
    if not isinstance(observation["qualityFlags"], list):
        raise ValueError("qualityFlags must be a list")
    if not isinstance(observation["synthetic"], bool):
        raise ValueError("synthetic must be boolean")
    return observation
