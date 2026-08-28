from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import tempfile
from pathlib import Path

from app.intelligence import EventIntelligenceService
from app.intelligence.forecast import ScenarioCatalogMatcher
from app.models import Coordinates, SensorState


EVENT_ID = "FP202506010024"
SENSOR_ID = "SSZJ-NODE-001"


class _Runtime:
    def __init__(self, state):
        self._state = state

    def state(self):
        return self._state


class _Status:
    value = "ready"


class _WaterState:
    status = _Status()


class _Nowcast:
    frames = []


class _Context:
    nowcast = _Nowcast()


class _MeteoState:
    status = _Status()
    context = _Context()


class _Repo:
    def __init__(self):
        self.sensor = None
        self.event = {
            "id": EVENT_ID,
            "name": "人民路 × 滨江大道",
            "district": "黄浦区",
            "eventType": "道路积水",
            "coordinates": {"lat": 31.2297, "lon": 121.4874},
            "currentDepthCm": 20.0,
            "riseRateCmMin": 1.8,
            "pipeLoadPercent": 91.0,
            "riskLevel": "HIGH",
            "startedAt": "2026-08-28T08:00:00+08:00",
            "durationSeconds": 600,
            "cameraId": "CAM-017",
        }
        self.forecast = {
            "eventId": EVENT_ID,
            "generatedAt": "2026-08-28T08:00:00+08:00",
            "frames": [
                {"timeKey": "NOW", "offsetMinutes": 0, "maxDepthCm": 20.0, "affectedAreaKm2": 0.01, "geometryUrl": "/now.geojson"},
                {"timeKey": "PLUS_10", "offsetMinutes": 10, "maxDepthCm": 25.0, "affectedAreaKm2": 0.02, "geometryUrl": "/10.geojson"},
                {"timeKey": "PLUS_30", "offsetMinutes": 30, "maxDepthCm": 35.0, "affectedAreaKm2": 0.03, "geometryUrl": "/30.geojson"},
            ],
        }

    def list_flood_points(self):
        return [{"id": "FP-001", "eventId": EVENT_ID, "sensorId": SENSOR_ID}]

    def get_event(self, event_id):
        return dict(self.event) if event_id == EVENT_ID else None

    def get_state(self, sensor_id):
        return self.sensor if sensor_id == SENSOR_ID else None

    def get_forecast(self, event_id):
        return dict(self.forecast) if event_id == EVENT_ID else None

    def get_analysis(self, event_id):
        return {
            "eventId": event_id,
            "riskSummary": "fixture",
            "causes": [{"label": "fixture", "weight": 1.0}],
            "forecastSummary": "fixture",
            "actions": [],
        }


def state(depth, observed):
    return SensorState(
        sensorId=SENSOR_ID,
        siteId="SITE-RML-BJDD",
        coordinates=Coordinates(lat=31.2297, lon=121.4874),
        depthMm=depth * 10,
        depthCm=depth,
        waterDetected=depth > 0,
        observedAt=observed,
        receivedAt=observed,
        transport="SIMULATOR",
        source="DEMO_DEVICE",
    )



def scenario_match_smoke(fixture_forecast):
    payload = {
        "featureRanges": {
            "currentDepthCm": [0, 60],
            "riseRateCmMin": [-2, 3],
            "pipeLoadPercent": [0, 100],
        },
        "scenarios": [
            {
                "eventId": EVENT_ID,
                "features": {"currentDepthCm": 30, "riseRateCmMin": 2, "pipeLoadPercent": 90},
                "frames": [
                    {"timeKey": "NOW", "maxDepthCm": 30},
                    {"timeKey": "PLUS_10", "maxDepthCm": 39},
                    {"timeKey": "PLUS_30", "maxDepthCm": 55},
                ],
            }
        ],
    }
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "catalog.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        matcher = ScenarioCatalogMatcher(path)
        result = matcher.match(
            event_id=EVENT_ID,
            features={"currentDepthCm": 30.0, "riseRateCmMin": 2.0, "pipeLoadPercent": 90.0},
            fixture_forecast=fixture_forecast,
            generated_at=datetime.now(timezone.utc),
        )
    assert result is not None
    assert result["method"] == "SCENARIO_LIBRARY"
    assert result["frames"][2]["maxDepthCm"] == 55.0


def main():
    repo = _Repo()
    service = EventIntelligenceService(
        repo,
        shanghai_water_realtime=_Runtime(_WaterState()),
        meteorology_realtime=_Runtime(_MeteoState()),
    )

    now = datetime.now(timezone.utc)
    first = state(20.0, now - timedelta(minutes=5))
    second = state(30.0, now)
    repo.sensor = first
    service.observe_sensor(first)
    repo.sensor = second
    service.observe_sensor(second)

    event = service.get_event(EVENT_ID)
    assert event is not None
    assert 1.9 <= event["riseRateCmMin"] <= 2.1, event
    assert event["riseRateSource"] == "ROBUST_MEDIAN_PAIRWISE_SLOPE"
    assert event["riskMethod"] == "RULE_WEIGHTED_V1"
    assert event["riskIndex"] >= 60

    forecast = service.get_forecast(EVENT_ID)
    assert forecast is not None
    assert forecast["method"] == "EMPIRICAL_BASELINE"
    plus30 = next(item for item in forecast["frames"] if item["timeKey"] == "PLUS_30")
    assert plus30["maxDepthCm"] > event["currentDepthCm"]
    assert plus30["upperDepthCm"] > plus30["lowerDepthCm"]

    analysis = service.get_analysis(EVENT_ID)
    assert analysis is not None
    assert analysis["method"] == "RULE_WEIGHTED_V1"
    assert analysis["riskSummary"] != "fixture"

    update = service.get_update_for_sensor(SENSOR_ID)
    assert update and update["event"]["id"] == EVENT_ID
    scenario_match_smoke(repo.forecast)

    print("INTELLIGENCE SMOKE: PASS")
    print(f"riseRate={event['riseRateCmMin']:.2f} cm/min")
    print(f"riskIndex={event['riskIndex']:.1f} level={event['riskLevel']}")
    print(f"forecastMethod={forecast['method']} +30={plus30['maxDepthCm']:.1f} cm")


if __name__ == "__main__":
    main()
