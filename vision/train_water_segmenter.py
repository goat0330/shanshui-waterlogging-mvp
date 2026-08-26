"""Train/evaluate the small RC2.3 water-mask candidate.

This command consumes an already acquired local Urban Flood Image Dataset
archive.  It uses a source-level holdout (Deepflood + Sazara -> WebCOOS),
reports an A/B against the current OpenCV mask, and writes the checkpoint only
to a caller-selected local path.  No raw data or checkpoint belongs in Git.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
import joblib
import numpy as np
from PIL import Image
from sklearn.linear_model import LogisticRegression

from .learned_segmentation import DEFAULT_SIZE, FEATURE_NAMES, feature_matrix
from .water_segmentation import segment_water


@dataclass(frozen=True)
class ImageMaskPair:
    dataset: str
    image_path: Path
    mask_path: Path


def _dataset_root(data_root: Path) -> Path:
    if (data_root / "Deepflood").is_dir():
        return data_root
    extracted = data_root / "extracted"
    if (extracted / "Deepflood").is_dir():
        return extracted
    raise FileNotFoundError(f"missing extracted Urban Flood Image Dataset: {data_root}")


def collect_pairs(data_root: str | Path) -> list[ImageMaskPair]:
    root = _dataset_root(Path(data_root))
    pairs: list[ImageMaskPair] = []
    for dataset in ("Deepflood", "Sazara", "WebCOOS"):
        dataset_root = root / dataset
        for image_path in sorted((dataset_root / "image").glob("*.jpg")):
            if dataset == "Sazara":
                mask_name = f"label_{image_path.stem.split('_', 1)[1]}.png"
            else:
                mask_name = f"{image_path.stem}.png"
            mask_path = dataset_root / "mask" / mask_name
            if mask_path.is_file():
                pairs.append(ImageMaskPair(dataset, image_path, mask_path))
    return pairs


def _load_pair(pair: ImageMaskPair) -> tuple[np.ndarray, np.ndarray]:
    image = np.asarray(Image.open(pair.image_path).convert("RGB"))
    mask = np.asarray(Image.open(pair.mask_path).convert("L"))
    return image, mask > 0


def _sample_pixels(
    image: np.ndarray,
    mask: np.ndarray,
    limit: int,
    seed: int,
) -> tuple[np.ndarray, np.ndarray]:
    features, shape = feature_matrix(image, size=DEFAULT_SIZE)
    small_mask = cv2.resize(
        mask.astype(np.uint8),
        (shape[1], shape[0]),
        interpolation=cv2.INTER_NEAREST,
    ).reshape(-1) > 0
    rng = np.random.default_rng(seed)
    positive = np.flatnonzero(small_mask)
    negative = np.flatnonzero(~small_mask)
    if not len(positive) or not len(negative):
        indices = rng.choice(len(features), size=min(limit, len(features)), replace=False)
    else:
        half = max(1, limit // 2)
        positive = rng.choice(positive, size=min(half, len(positive)), replace=False)
        negative = rng.choice(negative, size=min(half, len(negative)), replace=False)
        indices = np.concatenate([positive, negative])
    return features[indices], small_mask[indices].astype(np.int8)


def _metrics(prediction: np.ndarray, truth: np.ndarray) -> dict[str, float | int]:
    predicted = prediction.astype(bool)
    actual = truth.astype(bool)
    intersection = int(np.logical_and(predicted, actual).sum())
    union = int(np.logical_or(predicted, actual).sum())
    tp = intersection
    fp = int(np.logical_and(predicted, ~actual).sum())
    fn = int(np.logical_and(~predicted, actual).sum())
    return {
        "iou": round(intersection / union, 6) if union else 1.0,
        "dice": round((2 * intersection) / max(2 * intersection + fp + fn, 1), 6),
        "precision": round(tp / max(tp + fp, 1), 6),
        "recall": round(tp / max(tp + fn, 1), 6),
    }


def _mean_metrics(rows: list[dict[str, float | int]]) -> dict[str, float | int]:
    if not rows:
        return {"count": 0, "iou": None, "dice": None, "precision": None, "recall": None}
    return {
        "count": len(rows),
        **{name: round(float(np.mean([float(row[name]) for row in rows])), 6) for name in ("iou", "dice", "precision", "recall")},
    }


def _evaluate(
    pairs: list[ImageMaskPair],
    predictor: Any,
    examples_dir: Path | None,
    prefix: str,
) -> tuple[dict[str, Any], dict[str, dict[str, float | int]]]:
    rows: list[dict[str, float | int]] = []
    by_dataset: dict[str, list[dict[str, float | int]]] = {}
    for index, pair in enumerate(pairs):
        image, truth = _load_pair(pair)
        prediction = predictor(image)
        row = _metrics(prediction, truth)
        rows.append(row)
        by_dataset.setdefault(pair.dataset, []).append(row)
        if examples_dir is not None and index < 3:
            examples_dir.mkdir(parents=True, exist_ok=True)
            Image.fromarray((prediction.astype(np.uint8) * 255)).save(
                examples_dir / f"{prefix}-{pair.dataset}-{pair.image_path.stem}.png"
            )
            Image.fromarray((truth.astype(np.uint8) * 255)).save(
                examples_dir / f"truth-{pair.dataset}-{pair.image_path.stem}.png"
            )
    return _mean_metrics(rows), {dataset: _mean_metrics(items) for dataset, items in sorted(by_dataset.items())}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", required=True)
    parser.add_argument("--model-out", required=True)
    parser.add_argument("--metrics-out", required=True)
    parser.add_argument("--examples-dir")
    parser.add_argument("--pixels-per-image", type=int, default=384)
    parser.add_argument("--seed", type=int, default=23)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    pairs = collect_pairs(args.data_root)
    train_pairs = [pair for pair in pairs if pair.dataset in {"Deepflood", "Sazara"}]
    test_pairs = [pair for pair in pairs if pair.dataset == "WebCOOS"]
    if not train_pairs or not test_pairs:
        raise RuntimeError("source-level holdout requires Deepflood/Sazara train and WebCOOS test pairs")

    feature_rows: list[np.ndarray] = []
    label_rows: list[np.ndarray] = []
    sampled_pixels = 0
    for index, pair in enumerate(train_pairs):
        image, mask = _load_pair(pair)
        features, labels = _sample_pixels(image, mask, args.pixels_per_image, args.seed + index)
        feature_rows.append(features)
        label_rows.append(labels)
        sampled_pixels += len(labels)
    x_train = np.concatenate(feature_rows, axis=0)
    y_train = np.concatenate(label_rows, axis=0)
    model = LogisticRegression(
        class_weight="balanced",
        max_iter=200,
        random_state=args.seed,
        solver="liblinear",
    )
    model.fit(x_train, y_train)
    bundle = {
        "model": model,
        "feature_names": FEATURE_NAMES,
        "size": list(DEFAULT_SIZE),
        "threshold": 0.5,
        "candidate": "pixel_logistic_regression",
        "source_split": {"train": ["Deepflood", "Sazara"], "test": ["WebCOOS"]},
    }
    model_path = Path(args.model_out)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, model_path)

    def candidate_predictor(image: np.ndarray) -> np.ndarray:
        from .learned_segmentation import predict_water_mask

        return predict_water_mask(image, bundle, threshold=0.5).mask > 0

    def baseline_predictor(image: np.ndarray) -> np.ndarray:
        return segment_water(image).mask > 0

    examples_dir = Path(args.examples_dir) if args.examples_dir else None
    candidate_metrics, candidate_by_dataset = _evaluate(
        test_pairs, candidate_predictor, examples_dir, "candidate"
    )
    baseline_metrics, baseline_by_dataset = _evaluate(
        test_pairs, baseline_predictor, examples_dir, "baseline"
    )
    metrics = {
        "status": "PASS",
        "candidate": "pixel_logistic_regression",
        "task": "water_segmentation",
        "source": {
            "dataset": "Urban Flood Image Dataset",
            "resource": "https://www.hydroshare.org/resource/24866122a6ee456c8f7c80aa87a9abcb/",
            "declaredLicense": "CC BY 4.0",
            "mvpVerification": "VERIFIED_FOR_RESEARCH_MVP",
            "rightsReview": "DEFERRED_TO_USER",
            "runtimePolicy": "research_mvp_local_only",
        },
        "split": {
            "unit": "source_archive",
            "trainDatasets": ["Deepflood", "Sazara"],
            "testDatasets": ["WebCOOS"],
            "trainImages": len(train_pairs),
            "testImages": len(test_pairs),
            "sameImageAcrossSplit": False,
        },
        "features": list(FEATURE_NAMES),
        "sampledTrainPixels": sampled_pixels,
        "candidateMetrics": candidate_metrics,
        "candidateMetricsByDataset": candidate_by_dataset,
        "opencvBaselineMetrics": baseline_metrics,
        "opencvBaselineMetricsByDataset": baseline_by_dataset,
        "interpretation": "Held-out mask metrics only; not a production street-camera accuracy claim.",
        "notVerified": [
            "Shanghai domain transfer",
            "video temporal stability",
            "metric centimetre depth",
            "production checkpoint provenance",
        ],
    }
    metrics_path = Path(args.metrics_out)
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_path.write_text(json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"WATER_SEGMENTATION_CANDIDATE_PASS train={len(train_pairs)} test={len(test_pairs)} "
        f"candidate_iou={candidate_metrics['iou']} baseline_iou={baseline_metrics['iou']} "
        f"metrics={metrics_path.as_posix()} model={model_path.as_posix()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
