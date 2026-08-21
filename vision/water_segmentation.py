"""Small OpenCV water-mask baseline.

This is deliberately a visual candidate mask, not a trained flood-segmentation
model. Its output is evidence for review and is always reported as baseline.
"""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass(frozen=True)
class WaterSegmentation:
    mask: np.ndarray
    score: float
    water_fraction: float
    lower_fraction: float
    largest_component_fraction: float
    water_color_fraction: float
    lower_red_blue_contrast: float
    roughness: float
    method: str = "opencv_baseline"


def _analysis_image(image_rgb: np.ndarray, max_width: int = 960) -> np.ndarray:
    height, width = image_rgb.shape[:2]
    if width <= max_width:
        return image_rgb
    new_height = max(1, round(height * max_width / width))
    return cv2.resize(image_rgb, (max_width, new_height), interpolation=cv2.INTER_AREA)


def segment_water(image_rgb: np.ndarray) -> WaterSegmentation:
    small_rgb = _analysis_image(image_rgb)
    height, width = small_rgb.shape[:2]
    bgr = cv2.cvtColor(small_rgb, cv2.COLOR_RGB2BGR)
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

    y_grid = np.arange(height, dtype=np.float32)[:, None] / max(height - 1, 1)
    lower = np.broadcast_to(y_grid >= 0.28, (height, width))
    saturation = hsv[..., 1].astype(np.float32)
    value = hsv[..., 2].astype(np.float32)
    blue, green, red = [bgr[..., i].astype(np.float32) for i in range(3)]

    dx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    dy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    gradient = cv2.magnitude(dx, dy) / 8.0
    smooth_gradient = cv2.GaussianBlur(gradient, (0, 0), 2.0)
    lower_gradient = smooth_gradient[lower]
    gradient_limit = float(np.clip(np.percentile(lower_gradient, 58), 24.0, 78.0))

    # V1 deliberately favors visible brown/blue water chroma over generic gray
    # pavement; a neutral-color branch made dry streets fill the whole lower ROI.
    muddy = (red - blue > 8.0) & (red >= green * 0.96) & (saturation < 160)
    cool = (blue - red > 8.0) & (saturation < 160)
    vegetation = (green > red * 1.12) & (green > blue * 1.05) & (saturation > 40)
    reflective = value > 35
    color_candidate = (muddy | cool) & ~vegetation & reflective
    texture_candidate = smooth_gradient <= gradient_limit

    raw = (lower & color_candidate & texture_candidate).astype(np.uint8) * 255
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
    mask = cv2.morphologyEx(raw, cv2.MORPH_CLOSE, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))

    component_count, labels, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
    min_area = max(80, int(height * width * 0.0025))
    selected = np.zeros_like(mask)
    component_areas: list[int] = []
    for label in range(1, component_count):
        area = int(stats[label, cv2.CC_STAT_AREA])
        if area < min_area:
            continue
        x = int(stats[label, cv2.CC_STAT_LEFT])
        y = int(stats[label, cv2.CC_STAT_TOP])
        w = int(stats[label, cv2.CC_STAT_WIDTH])
        h = int(stats[label, cv2.CC_STAT_HEIGHT])
        touches_bottom = y + h >= height * 0.86
        broad_enough = w >= width * 0.08 or h >= height * 0.15
        if touches_bottom or broad_enough:
            selected[labels == label] = 255
            component_areas.append(area)

    if not component_areas:
        selected = np.zeros_like(mask)
    else:
        selected = cv2.morphologyEx(selected, cv2.MORPH_CLOSE, kernel)

    mask_fraction = float(np.mean(selected > 0))
    lower_fraction = float(np.mean(selected[int(height * 0.55) :] > 0))
    largest_fraction = float(max(component_areas, default=0) / max(height * width, 1))
    selected_pixels = selected > 0
    water_color = (np.abs(red - blue) > 8.0) & (saturation < 160)
    water_color_fraction = float(np.mean(water_color[selected_pixels])) if np.any(selected_pixels) else 0.0
    lower_red_blue_contrast = float(np.mean((red - blue)[int(height * 0.55) :]))
    roughness = float(np.mean(smooth_gradient[selected > 0])) if np.any(selected) else float(np.mean(smooth_gradient))
    low_texture_score = float(np.clip((65.0 - roughness) / 65.0, 0.0, 1.0))
    extent_score = float(np.clip(largest_fraction / 0.20, 0.0, 1.0))
    lower_score = float(np.clip(lower_fraction / 0.60, 0.0, 1.0))
    score = float(np.clip(0.42 * extent_score + 0.34 * lower_score + 0.24 * low_texture_score, 0.0, 1.0))

    if score < 0.22 or largest_fraction < 0.012 or lower_fraction < 0.018:
        selected = np.zeros_like(selected)
        mask_fraction = 0.0
        lower_fraction = 0.0
        largest_fraction = 0.0
        water_color_fraction = 0.0

    if selected.shape != image_rgb.shape[:2]:
        selected = cv2.resize(selected, (image_rgb.shape[1], image_rgb.shape[0]), interpolation=cv2.INTER_NEAREST)

    return WaterSegmentation(
        mask=selected,
        score=score,
        water_fraction=mask_fraction,
        lower_fraction=lower_fraction,
        largest_component_fraction=largest_fraction,
        water_color_fraction=water_color_fraction,
        lower_red_blue_contrast=lower_red_blue_contrast,
        roughness=roughness,
    )
