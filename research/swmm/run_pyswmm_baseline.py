from __future__ import annotations

import argparse
import csv
from pathlib import Path

from pyswmm import Nodes, Simulation


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a PySWMM baseline and export one node depth time series.")
    parser.add_argument("inp")
    parser.add_argument("--node-id", required=True)
    parser.add_argument("--out", default="research/swmm/runtime/fp001-node-depth.csv")
    parser.add_argument("--sample-every", type=int, default=1)
    args = parser.parse_args()

    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    with Simulation(str(Path(args.inp).resolve())) as sim:
        node = Nodes(sim)[args.node_id]
        for index, _ in enumerate(sim):
            if index % max(1, args.sample_every):
                continue
            rows.append((sim.current_time.isoformat(), float(node.depth)))

    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["time", "nodeDepthModelUnits"])
        writer.writerows(rows)
    print(f"rows={len(rows)} out={output}")
    print("NOTE: node depth uses model units; do not relabel as cm without unit conversion/model validation.")


if __name__ == "__main__":
    main()
