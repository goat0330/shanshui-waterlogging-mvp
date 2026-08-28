from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from urllib.request import Request, urlopen

SENSOR_ID = "SSZJ-NODE-001"
EVENT_ID = "FP202506010024"


def request_json(url: str, *, method: str = "GET", payload: dict | None = None):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"} if data else {}
    with urlopen(Request(url, data=data, headers=headers, method=method), timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Send two explicit DEMO_DEVICE observations to validate dynamic intelligence.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--start-depth-cm", type=float, default=20.0)
    parser.add_argument("--end-depth-cm", type=float, default=30.0)
    parser.add_argument("--minutes", type=float, default=5.0)
    args = parser.parse_args()

    now = datetime.now(timezone.utc)
    samples = [
        (args.start_depth_cm, now - timedelta(minutes=max(args.minutes, 0.5)), 900001),
        (args.end_depth_cm, now, 900002),
    ]
    for depth, observed_at, sequence in samples:
        request_json(
            f"{args.base_url}/api/v1/telemetry/observations",
            method="POST",
            payload={
                "sensorId": SENSOR_ID,
                "observedAt": observed_at.isoformat(),
                "depthMm": depth * 10,
                "sequence": sequence,
                "transport": "SIMULATOR",
            },
        )

    event = request_json(f"{args.base_url}/api/v1/flood-events/{EVENT_ID}")
    risk = request_json(f"{args.base_url}/api/v1/flood-events/{EVENT_ID}/risk")
    forecast = request_json(f"{args.base_url}/api/v1/flood-events/{EVENT_ID}/forecast")
    print("DEMO ONLY — synthetic telemetry injected through the real telemetry API")
    print(f"depth={event['currentDepthCm']:.1f} cm rise={event['riseRateCmMin']:.2f} cm/min source={event.get('riseRateSource')}")
    print(f"risk={risk['riskIndex']:.1f}/100 level={risk['riskLevel']} confidence={risk['confidence']:.2f} method={risk['method']}")
    for frame in forecast.get("frames", []):
        print(f"{frame['timeKey']}: {frame['maxDepthCm']:.1f} cm [{frame.get('lowerDepthCm')}–{frame.get('upperDepthCm')}] method={forecast.get('method')}")


if __name__ == "__main__":
    main()
