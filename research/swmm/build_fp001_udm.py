from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

FP001_LON = 121.4874
FP001_LAT = 31.2297


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a synthetic FP-001 urban drainage model with SWMManywhere.")
    parser.add_argument("--base-dir", default="research/swmm/runtime")
    parser.add_argument("--project", default="fp001_synthetic_udm")
    parser.add_argument("--half-span-deg", type=float, default=0.015, help="~3 km square around FP-001 at Shanghai latitude.")
    parser.add_argument("--no-run", action="store_true")
    args = parser.parse_args()

    base_dir = Path(args.base_dir).resolve()
    base_dir.mkdir(parents=True, exist_ok=True)
    span = max(0.003, min(args.half_span_deg, 0.05))
    bbox = [FP001_LON - span, FP001_LAT - span, FP001_LON + span, FP001_LAT + span]

    config = base_dir / f"{args.project}.yml"
    config.write_text(
        f"base_dir: {base_dir.as_posix()}\n"
        f"project: {args.project}\n"
        f"bbox: [{bbox[0]:.6f},{bbox[1]:.6f},{bbox[2]:.6f},{bbox[3]:.6f}]\n",
        encoding="utf-8",
    )
    print(f"config={config}")
    print(f"bbox={bbox}")
    print("classification=SYNTHETIC_UDM / NOT_OFFICIAL_NETWORK / RESEARCH_MVP")

    if not args.no_run:
        subprocess.run(
            [sys.executable, "-m", "swmmanywhere", f"--config_path={config}"],
            check=True,
        )
        expected = base_dir / args.project / "bbox_1" / "model_1" / "model_1.inp"
        print(f"expected_model={expected}")


if __name__ == "__main__":
    main()
