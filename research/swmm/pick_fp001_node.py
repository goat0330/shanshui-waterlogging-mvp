from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

FP001 = (121.4874, 31.2297)


def haversine_m(lon1, lat1, lon2, lat2):
    radius = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(a))


def main() -> None:
    parser = argparse.ArgumentParser(description="Pick the synthetic SWMM node nearest FP-001.")
    parser.add_argument("nodes_geojson")
    args = parser.parse_args()
    payload = json.loads(Path(args.nodes_geojson).read_text(encoding="utf-8"))
    candidates = []
    for feature in payload.get("features", []):
        geometry = feature.get("geometry") or {}
        if geometry.get("type") != "Point":
            continue
        coords = geometry.get("coordinates") or []
        if len(coords) < 2:
            continue
        props = feature.get("properties") or {}
        node_id = next((props.get(key) for key in ("id", "name", "node_id", "nodeId") if props.get(key)), None)
        if node_id is None:
            continue
        distance = haversine_m(FP001[0], FP001[1], float(coords[0]), float(coords[1]))
        candidates.append((distance, str(node_id), coords))
    if not candidates:
        raise SystemExit("No point feature with id/name/node_id found.")
    distance, node_id, coords = min(candidates)
    print(json.dumps({"nodeId": node_id, "distanceM": round(distance, 1), "coordinates": coords}, ensure_ascii=False))


if __name__ == "__main__":
    main()
