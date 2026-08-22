"""Optional mask metrics; without labelled GT this remains explicitly unverified."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image


def _binary(path: Path) -> np.ndarray:
    return np.asarray(Image.open(path).convert("L")) > 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pred", required=True)
    parser.add_argument("--gt", required=True)
    args = parser.parse_args()
    pred_paths = {path.name: path for path in Path(args.pred).glob("*.png")}
    gt_paths = {path.name: path for path in Path(args.gt).glob("*.png")}
    names = sorted(pred_paths.keys() & gt_paths.keys())
    if not names:
        print("NOT_VERIFIED: NO_MATCHED_GT")
        return 2
    scores = []
    for name in names:
        pred = _binary(pred_paths[name])
        gt = _binary(gt_paths[name])
        if pred.shape != gt.shape:
            raise ValueError(f"mask shape mismatch: {name}")
        intersection = float(np.logical_and(pred, gt).sum())
        union = float(np.logical_or(pred, gt).sum())
        scores.append(intersection / union if union else 1.0)
    print(f"matched={len(names)} mean_iou={sum(scores) / len(scores):.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
