from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen


DEFAULT_SEQUENCE_FILE = Path(__file__).resolve().parents[2] / "contracts" / "fixtures" / "telemetry-sequence.json"


def post_observation(base_url: str, payload: dict[str, object]) -> dict[str, object]:
    request = Request(
        f"{base_url.rstrip('/')}/api/v1/telemetry/observations",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Accept": "application/json", "Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=5) as response:
        result = json.loads(response.read().decode("utf-8"))
        if response.status != 201:
            raise RuntimeError(f"telemetry POST returned {response.status}: {result}")
        return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Post the checked-in synthetic telemetry sequence.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--sequence-file", type=Path, default=DEFAULT_SEQUENCE_FILE)
    timing = parser.add_mutually_exclusive_group()
    timing.add_argument("--realtime", action="store_true", help="wait for each fixture delayMs")
    timing.add_argument("--no-wait", action="store_true", help="fast mode; the default")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    with args.sequence_file.open("r", encoding="utf-8") as file:
        sequence_fixture = json.load(file)

    sensor_id = sequence_fixture["sensorId"]
    steps = sequence_fixture["sequence"]
    for index, step in enumerate(steps, start=1):
        if args.realtime:
            time.sleep(step.get("delayMs", 0) / 1000)
        payload = {
            "sensorId": sensor_id,
            "observedAt": datetime.now(timezone.utc).isoformat(),
            "depthMm": step["depthMm"],
            "sequence": index,
            "transport": "SIMULATOR",
        }
        result = post_observation(args.base_url, payload)
        print(f"POST {index}/{len(steps)} sensorId={sensor_id} depthMm={result['depthMm']}")


if __name__ == "__main__":
    main()
