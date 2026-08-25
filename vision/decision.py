"""Deterministic product decision projection over VisionDepth evidence."""

from __future__ import annotations

from typing import Any


TRAFFIC_STATUSES = {"NORMAL", "CAUTION", "NOT_RECOMMENDED", "PROHIBITED"}
RECOMMENDATIONS = {
    "NORMAL": "NORMAL_PASSAGE",
    "CAUTION": "CAUTION_PASSAGE",
    "NOT_RECOMMENDED": "DO_NOT_PASS",
    "PROHIBITED": "NO_PASSAGE",
}


def _decision_depth(depth: dict[str, Any], flood_detected: bool) -> tuple[float, str]:
    if not flood_detected:
        return 0.0, "NO_FLOOD"

    estimated = depth.get("estimatedDepthCm")
    if estimated is not None:
        return round(float(estimated), 1), "ESTIMATED_REFERENCE"

    approximate = depth.get("approximateDepthCm")
    if approximate is not None:
        return round(float(approximate), 1), "APPROXIMATE_RANGE"

    level = int(depth["level"])
    lower, upper = depth["rangeCm"]
    if lower is None:
        raise ValueError("flood decision requires a finite lower depth bound")
    if upper is None:
        return float(lower), "LEVEL_LOWER_BOUND"
    return round((float(lower) + float(upper)) / 2.0, 1), "LEVEL_RANGE_MIDPOINT"


def _traffic_status(decision_depth_cm: float, flood_detected: bool) -> str:
    if not flood_detected:
        return "NORMAL"
    if decision_depth_cm < 10:
        return "NORMAL"
    if decision_depth_cm < 20:
        return "CAUTION"
    if decision_depth_cm < 30:
        return "NOT_RECOMMENDED"
    return "PROHIBITED"


def project_decision(observation: dict[str, Any]) -> dict[str, Any]:
    """Project evidence into product traffic guidance without changing evidence."""

    flood_detected = bool(observation["floodDetected"])
    decision_depth_cm, depth_source = _decision_depth(observation["depth"], flood_detected)
    traffic_status = _traffic_status(decision_depth_cm, flood_detected)
    return {
        "floodDetected": flood_detected,
        "decisionDepthCm": decision_depth_cm,
        "trafficStatus": traffic_status,
        "recommendation": RECOMMENDATIONS[traffic_status],
        "decisionDepthSource": depth_source,
    }
