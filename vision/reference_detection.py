"""Conservative reference-object evidence from OpenCV-only detectors."""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from .schema import clamp


REFERENCE_TYPES = {
    "PERSON_REFERENCE",
    "VEHICLE_REFERENCE",
    "TRAFFIC_SIGN_REFERENCE",
    "FIXED_CAMERA_REFERENCE",
}


@dataclass(frozen=True)
class ReferenceEvidence:
    type: str
    bbox: tuple[int, int, int, int]
    confidence: float
    water_overlap_ratio: float
    waterline_y: float | None
    reliable: bool
    detector: str

    def as_dict(self) -> dict[str, object]:
        x, y, width, height = self.bbox
        return {
            "type": self.type,
            "bbox": {"x": x, "y": y, "width": width, "height": height},
            "confidence": round(self.confidence, 3),
            "waterOverlapRatio": round(self.water_overlap_ratio, 3),
            "waterlineY": None if self.waterline_y is None else round(self.waterline_y, 3),
            "reliable": self.reliable,
            "detector": self.detector,
        }


def _waterline(mask: np.ndarray, bbox: tuple[int, int, int, int]) -> float | None:
    x, y, width, height = bbox
    image_height, image_width = mask.shape[:2]
    x0 = max(0, x - max(4, width // 3))
    x1 = min(image_width, x + width + max(4, width // 3))
    if x0 >= x1:
        return None
    region = mask[:, x0:x1] > 0
    ys = np.where(region)[0]
    if ys.size == 0:
        return None
    # Ignore isolated upper false positives; a flood candidate must be below 20%.
    ys = ys[ys >= mask.shape[0] * 0.20]
    if ys.size == 0:
        return None
    return float(np.percentile(ys, 10) / max(mask.shape[0] - 1, 1))


def _person_evidence(image_rgb: np.ndarray, water_mask: np.ndarray) -> list[ReferenceEvidence]:
    height, width = image_rgb.shape[:2]
    scale = min(1.0, 1200.0 / max(width, 1))
    small = cv2.resize(image_rgb, (max(1, round(width * scale)), max(1, round(height * scale))))
    hog = cv2.HOGDescriptor()
    hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())
    boxes, weights = hog.detectMultiScale(small, winStride=(8, 8), padding=(16, 16), scale=1.05)
    evidence: list[ReferenceEvidence] = []
    for box, weight in zip(boxes, weights):
        sx, sy, sw, sh = [int(v) for v in box]
        x = round(sx / scale)
        y = round(sy / scale)
        w = round(sw / scale)
        h = round(sh / scale)
        if h < max(40, height * 0.05) or w < max(12, width * 0.015):
            continue
        x = max(0, min(width - 1, x))
        y = max(0, min(height - 1, y))
        w = max(1, min(width - x, w))
        h = max(1, min(height - y, h))
        score = clamp(0.42 + (float(weight) - 0.25) * 0.25, 0.25, 0.9)
        roi = water_mask[y : y + h, x : x + w]
        overlap = float(np.mean(roi > 0)) if roi.size else 0.0
        waterline = _waterline(water_mask, (x, y, w, h))
        bottom_band = water_mask[y + max(0, round(h * 0.72)) : y + h, x : x + w]
        bottom_overlap = float(np.mean(bottom_band > 0)) if bottom_band.size else 0.0
        reliable = bool(score >= 0.60 and (overlap >= 0.035 or bottom_overlap >= 0.08) and y < height * 0.85)
        evidence.append(
            ReferenceEvidence(
                "PERSON_REFERENCE",
                (x, y, w, h),
                score,
                overlap,
                waterline,
                reliable,
                "opencv_hog",
            )
        )
    return evidence


def _traffic_sign_evidence(image_rgb: np.ndarray, water_mask: np.ndarray) -> list[ReferenceEvidence]:
    """Find only compact red/orange sign-like blobs; cones remain low-confidence."""

    hsv = cv2.cvtColor(cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR), cv2.COLOR_BGR2HSV)
    red = cv2.inRange(hsv, (0, 80, 70), (12, 255, 255)) | cv2.inRange(hsv, (168, 70, 60), (180, 255, 255))
    orange = cv2.inRange(hsv, (8, 90, 80), (25, 255, 255))
    colored = cv2.morphologyEx(red | orange, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    contours, _ = cv2.findContours(colored, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    height, width = image_rgb.shape[:2]
    evidence: list[ReferenceEvidence] = []
    for contour in contours:
        area = cv2.contourArea(contour)
        x, y, w, h = cv2.boundingRect(contour)
        if area < width * height * 0.00025 or area > width * height * 0.04:
            continue
        if y > height * 0.75 or w < 8 or h < 8:
            continue
        aspect = w / max(h, 1)
        if not 0.35 <= aspect <= 2.8:
            continue
        compactness = 4 * np.pi * area / max(cv2.arcLength(contour, True) ** 2, 1.0)
        if compactness < 0.18:
            continue
        roi = water_mask[y : y + h, x : x + w]
        overlap = float(np.mean(roi > 0)) if roi.size else 0.0
        waterline = _waterline(water_mask, (x, y, w, h))
        score = clamp(0.25 + min(0.3, compactness * 0.25) + min(0.2, area / (width * height) * 4))
        reliable = bool(score >= 0.42 and overlap >= 0.04)
        evidence.append(
            ReferenceEvidence(
                "TRAFFIC_SIGN_REFERENCE",
                (x, y, w, h),
                score,
                overlap,
                waterline,
                reliable,
                "opencv_color_heuristic",
            )
        )
    return evidence


def detect_references(image_rgb: np.ndarray, water_mask: np.ndarray) -> list[ReferenceEvidence]:
    """Return evidence only; ordinary bounding boxes never become depth by themselves."""

    references = _person_evidence(image_rgb, water_mask)
    references.extend(_traffic_sign_evidence(image_rgb, water_mask))
    references.sort(key=lambda item: (not item.reliable, -item.confidence))
    return references[:8]
