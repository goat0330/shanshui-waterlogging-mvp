"""Optional learned water-mask adapter for the local verified MVP candidate.

The adapter loads only an explicit/local checkpoint. It never downloads weights
and never converts a water mask into calibrated centimetres.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import cv2
import numpy as np


FEATURE_NAMES = (
    "r",
    "g",
    "b",
    "h",
    "s",
    "v",
    "x",
    "y",
    "gradient",
)
DEFAULT_SIZE = (128, 128)


@dataclass(frozen=True)
class LearnedWaterMask:
    mask: np.ndarray
    mean_probability: float
    threshold: float
    method: str = "pixel_logistic_regression"


def feature_matrix(image_rgb: np.ndarray, size: tuple[int, int] = DEFAULT_SIZE) -> tuple[np.ndarray, tuple[int, int]]:
    """Create the fixed low-cost feature matrix used by training and inference."""
    width, height = size
    small = cv2.resize(image_rgb, (width, height), interpolation=cv2.INTER_AREA)
    rgb = small.astype(np.float32) / 255.0
    bgr = cv2.cvtColor(small, cv2.COLOR_RGB2BGR)
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV).astype(np.float32)
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY).astype(np.float32)
    dx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    dy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    gradient = np.clip(cv2.magnitude(dx, dy) / 360.0, 0.0, 1.0)
    y_grid, x_grid = np.mgrid[0:height, 0:width].astype(np.float32)
    x_grid /= max(width - 1, 1)
    y_grid /= max(height - 1, 1)
    features = np.column_stack([
        rgb[..., 0].ravel(),
        rgb[..., 1].ravel(),
        rgb[..., 2].ravel(),
        (hsv[..., 0] / 179.0).ravel(),
        (hsv[..., 1] / 255.0).ravel(),
        (hsv[..., 2] / 255.0).ravel(),
        x_grid.ravel(),
        y_grid.ravel(),
        gradient.ravel(),
    ])
    return features, (height, width)


@lru_cache(maxsize=2)
def _load_checkpoint_cached(resolved_path: str) -> dict[str, object]:
    import joblib

    bundle = joblib.load(resolved_path)
    if not isinstance(bundle, dict) or tuple(bundle.get("feature_names", ())) != FEATURE_NAMES:
        raise ValueError("unsupported learned segmentation checkpoint")
    model = bundle.get("model")
    if model is None or not callable(getattr(model, "predict_proba", None)):
        raise ValueError("learned segmentation checkpoint has no probability model")
    return bundle


def load_checkpoint(path: str | Path) -> dict[str, object]:
    """Load and validate an explicit local joblib checkpoint once per process."""
    return _load_checkpoint_cached(str(Path(path).expanduser().resolve()))


def predict_water_mask(
    image_rgb: np.ndarray,
    checkpoint: str | Path | dict[str, object],
    threshold: float = 0.5,
) -> LearnedWaterMask:
    """Predict a water mask; no metric depth is inferred."""
    bundle = load_checkpoint(checkpoint) if not isinstance(checkpoint, dict) else checkpoint
    model = bundle["model"]
    size = tuple(bundle.get("size", DEFAULT_SIZE))
    features, small_shape = feature_matrix(image_rgb, size=size)
    probabilities = model.predict_proba(features)[:, 1]
    small_mask = (probabilities.reshape(small_shape) >= threshold).astype(np.uint8) * 255
    mask = cv2.resize(small_mask, (image_rgb.shape[1], image_rgb.shape[0]), interpolation=cv2.INTER_NEAREST)
    return LearnedWaterMask(mask=mask, mean_probability=float(np.mean(probabilities)), threshold=threshold)
