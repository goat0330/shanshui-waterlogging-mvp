from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

FEATURES = ("currentDepthCm", "riseRateCmMin", "forecastRain30Mm", "pipeLoadPercent")
DEPTHS = (("NOW", "nowCm", 0), ("PLUS_10", "plus10Cm", 10), ("PLUS_30", "plus30Cm", 30))


def number(row: dict[str, str], key: str) -> float | None:
    raw = (row.get(key) or "").strip()
    return None if not raw else float(raw)


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert reviewed SWMM scenario summaries to Qixiao forecast-scenarios.json.")
    parser.add_argument("csv", help="CSV created from reviewed PySWMM/SWMM batch results")
    parser.add_argument("--out", default="data/runtime/forecast-scenarios.json")
    parser.add_argument("--event-id", default="FP202506010024")
    args = parser.parse_args()

    rows = list(csv.DictReader(Path(args.csv).open("r", encoding="utf-8-sig", newline="")))
    scenarios = []
    values_by_feature: dict[str, list[float]] = {key: [] for key in FEATURES}
    for index, row in enumerate(rows, start=1):
        features = {}
        for key in FEATURES:
            value = number(row, key)
            if value is not None:
                features[key] = value
                values_by_feature[key].append(value)
        if len(features) < 2:
            raise SystemExit(f"row {index}: at least two numeric forecast features are required")
        frames = []
        for time_key, column, offset in DEPTHS:
            depth = number(row, column)
            if depth is None:
                raise SystemExit(f"row {index}: missing {column}")
            frame = {"timeKey": time_key, "offsetMinutes": offset, "maxDepthCm": depth}
            lower = number(row, column.replace("Cm", "LowerCm"))
            upper = number(row, column.replace("Cm", "UpperCm"))
            if lower is not None:
                frame["lowerDepthCm"] = lower
            if upper is not None:
                frame["upperDepthCm"] = upper
            frames.append(frame)
        scenarios.append({
            "scenarioId": (row.get("scenarioId") or f"SWMM-{index:04d}").strip(),
            "eventId": args.event_id,
            "features": features,
            "frames": frames,
        })

    ranges = {}
    for key, values in values_by_feature.items():
        if not values:
            continue
        minimum, maximum = min(values), max(values)
        if minimum == maximum:
            maximum = minimum + 1.0
        ranges[key] = [minimum, maximum]

    payload = {
        "source": "REVIEWED_SWMM_SCENARIO_RUNS",
        "modelClassification": "SYNTHETIC_UDM_RESEARCH_MVP",
        "featureRanges": ranges,
        "scenarios": scenarios,
    }
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"scenarios={len(scenarios)} out={output}")
    print("Runtime provider becomes SCENARIO_LIBRARY only when live features produce a sufficiently close match.")


if __name__ == "__main__":
    main()
