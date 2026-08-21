from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, Request, build_opener

from app.config import load_settings
from app.main import app, repository, sensor_repository

try:
    import websocket
except ImportError:
    websocket = None


PORT = int(os.environ.get("SMOKE_PORT", "8765"))
BASE_URL = f"http://127.0.0.1:{PORT}"
LOCAL_OPENER = build_opener(ProxyHandler({}))


def request(path: str, method: str = "GET", payload: dict[str, object] | None = None) -> tuple[int, object]:
    headers = {"Accept": "application/json"}
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    try:
        with LOCAL_OPENER.open(
            Request(f"{BASE_URL}{path}", data=data, headers=headers, method=method),
            timeout=3,
        ) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        return error.code, json.loads(error.read().decode("utf-8"))


def wait_until_ready() -> None:
    for _ in range(40):
        try:
            status, _ = request("/api/v1/dashboard/overview")
            if status == 200:
                return
        except (URLError, TimeoutError, ConnectionError):
            pass
        time.sleep(0.25)
    raise RuntimeError("uvicorn did not become ready within 10 seconds")


def main() -> None:
    assert app.title == "Shanshui Waterlogging MVP API"
    backend_dir = Path(__file__).resolve().parent
    settings = load_settings()
    assert settings.repository_backend == "memory"
    assert repository.backend == "memory"
    assert (backend_dir / "alembic.ini").exists()
    assert (backend_dir / ".env.example").read_text(encoding="utf-8").find("REPOSITORY_BACKEND=memory") >= 0
    migration = backend_dir / "alembic" / "versions" / "0001_v1_persistence.py"
    migration_text = migration.read_text(encoding="utf-8")
    for table_name in [
        "sites",
        "sensors",
        "sensor_observations",
        "sensor_latest_state",
        "flood_points",
        "sensor_flood_mappings",
        "flood_events",
        "forecast_frames",
        "cameras",
    ]:
        assert f'"{table_name}"' in migration_text
    assert "CREATE EXTENSION IF NOT EXISTS postgis" in migration_text
    assert "create_all(" not in migration_text
    print("PASS memory default and migration configuration")
    formal_paths = {
        "/api/v1/dashboard/overview",
        "/api/v1/rainfall/current",
        "/api/v1/rainfall/stations/ranking",
        "/api/v1/flood-points",
        "/api/v1/flood-events/{event_id}",
        "/api/v1/flood-events/{event_id}/forecast",
        "/api/v1/flood-events/{event_id}/analysis",
        "/api/v1/cameras",
        "/api/v1/cameras/{camera_id}",
        "/api/v1/scenarios/{scenario_id}/timeline",
    }
    telemetry_paths = {
        "/api/v1/telemetry/observations",
        "/api/v1/sensors/{sensor_id}",
    }
    spec = app.openapi()
    assert set(spec["paths"]) == formal_paths | telemetry_paths
    assert spec["components"]["schemas"]["RiskLevel"]["enum"] == ["NORMAL", "WARNING", "HIGH", "CRITICAL"]
    assert spec["components"]["schemas"]["ForecastKey"]["enum"] == ["NOW", "PLUS_10", "PLUS_30"]
    assert spec["components"]["schemas"]["TelemetryTransport"]["enum"] == ["WIFI", "CELLULAR_4G", "SIMULATOR"]
    assert spec["paths"]["/api/v1/telemetry/observations"]["post"]["operationId"] == "createTelemetryObservation"
    assert spec["paths"]["/api/v1/sensors/{sensor_id}"]["get"]["operationId"] == "getSensorState"
    assert set(spec["components"]["schemas"]["TelemetryObservation"]["required"]) == {
        "sensorId",
        "observedAt",
        "depthMm",
    }
    assert spec["components"]["schemas"]["TelemetryObservation"]["additionalProperties"] is False
    assert set(spec["components"]["schemas"]["SensorState"]["required"]) == {
        "sensorId",
        "siteId",
        "coordinates",
        "depthMm",
        "depthCm",
        "waterDetected",
        "observedAt",
        "receivedAt",
    }
    assert spec["components"]["schemas"]["SensorState"]["additionalProperties"] is False
    ranking_schema = spec["components"]["schemas"]["RainfallStationRankingItem"]
    assert set(ranking_schema["required"]) == {"stationId", "stationName", "intensityMmH"}
    assert ranking_schema["additionalProperties"] is False
    assert spec["paths"]["/api/v1/rainfall/stations/ranking"]["get"]["operationId"] == "listRainfallStationRanking"
    registry_entry = sensor_repository.get_entry("SSZJ-NODE-001")
    assert registry_entry is not None
    assert registry_entry.sensorType.value == "WATER_DEPTH"
    assert registry_entry.enabled is True
    forecast_adapter = repository.forecast_adapter
    forecast_fixture = forecast_adapter.get("FP202506010024")
    assert forecast_fixture is not None
    assert [frame["timeKey"] for frame in forecast_fixture["frames"]] == ["NOW", "PLUS_10", "PLUS_30"]
    forecast_offsets = [frame["offsetMinutes"] for frame in forecast_fixture["frames"]]
    assert forecast_offsets == sorted(forecast_offsets)
    assert all(frame["maxDepthCm"] >= 0 and frame["affectedAreaKm2"] >= 0 for frame in forecast_fixture["frames"])
    analysis_adapter = repository.analysis_adapter
    assert analysis_adapter.source == "DEMO_SYNTHETIC_FIXTURE"
    assert analysis_adapter.synthetic is True
    assert analysis_adapter.get("FP202506010024") is not None
    print("PASS OpenAPI formal paths/enums, SensorRegistryEntry, and adapter fixture validation")

    websocket_client = None
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(PORT)],
        cwd=Path(__file__).resolve().parent,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        wait_until_ready()
        with LOCAL_OPENER.open(
            Request(
                f"{BASE_URL}/api/v1/dashboard/overview",
                headers={"Accept": "application/json", "Origin": "http://localhost:5173"},
            ),
            timeout=3,
        ) as response:
            assert response.headers.get("access-control-allow-origin") == "*"
        print("PASS CORS http://localhost:5173")

        paths = [
            "/api/v1/dashboard/overview",
            "/api/v1/rainfall/current",
            "/api/v1/rainfall/stations/ranking",
            "/api/v1/flood-points",
            "/api/v1/flood-events/FP202506010024",
            "/api/v1/flood-events/FP202506010024/forecast",
            "/api/v1/flood-events/FP202506010024/analysis",
            "/api/v1/cameras",
            "/api/v1/cameras/CAM-017",
            "/api/v1/scenarios/SHANGHAI-DEMO-001/timeline",
        ]
        for path in paths:
            status, payload = request(path)
            assert status == 200, (path, status, payload)
            json.dumps(payload, ensure_ascii=False)
            print(f"PASS 200 {path}")

        status, ranking = request("/api/v1/rainfall/stations/ranking")
        assert status == 200, (status, ranking)
        assert all(set(item) == {"stationId", "stationName", "intensityMmH"} for item in ranking)
        intensities = [item["intensityMmH"] for item in ranking]
        assert all(value >= 0 for value in intensities)
        assert intensities == sorted(intensities, reverse=True)
        json.dumps(ranking, ensure_ascii=False)
        print("PASS rainfall station ranking intensity order and response shape")

        status, forecast = request("/api/v1/flood-events/FP202506010024/forecast")
        assert status == 200
        assert [frame["timeKey"] for frame in forecast["frames"]] == ["NOW", "PLUS_10", "PLUS_30"]
        offsets = [frame["offsetMinutes"] for frame in forecast["frames"]]
        assert offsets == sorted(offsets)
        assert all(frame["maxDepthCm"] >= 0 and frame["affectedAreaKm2"] >= 0 for frame in forecast["frames"])
        json.dumps(forecast, ensure_ascii=False)
        status, analysis = request("/api/v1/flood-events/FP202506010024/analysis")
        assert status == 200
        assert set(analysis) == {"eventId", "riskSummary", "causes", "forecastSummary", "actions"}
        assert "source" not in analysis
        json.dumps(analysis, ensure_ascii=False)
        print("PASS forecast frame constraints and synthetic analysis response shape")

        status, payload = request("/api/v1/sensors/SSZJ-NODE-001")
        assert status == 404, (status, payload)
        assert isinstance(payload, dict) and payload.get("detail", {}).get("code") == "NOT_FOUND"
        print("PASS 404 known sensor without state")

        observation_request = {
            "sensorId": "SSZJ-NODE-001",
            "observedAt": "2026-08-21T14:30:00+08:00",
            "depthMm": 286,
            "sequence": 42,
            "transport": "SIMULATOR",
            "batteryMv": 3920,
            "signalDbm": -61,
        }
        if websocket is not None:
            websocket_client = websocket.create_connection(f"ws://127.0.0.1:{PORT}/ws/v1/realtime", timeout=20)
            started = json.loads(websocket_client.recv())
            assert started["type"] == "scenario.started"
            print("PASS WS scenario.started")
        else:
            print("SKIP WS sensor.updated (websocket-client is not installed)")

        status, observation = request(
            "/api/v1/telemetry/observations",
            method="POST",
            payload=observation_request,
        )
        assert status in (200, 201), (status, observation)
        assert status == 201
        assert observation["sensorId"] == "SSZJ-NODE-001"
        assert observation["siteId"] == "SITE-RML-BJDD"
        assert observation["coordinates"] == {"lat": 31.2297, "lon": 121.4874}
        assert observation["depthMm"] == 286
        assert observation["depthCm"] == 28.6
        assert observation["waterDetected"] is True
        assert observation["source"] == "DEMO_DEVICE"
        assert "receivedAt" in observation
        datetime.fromisoformat(observation["receivedAt"])
        assert "riskLevel" not in observation
        assert "riseRateCmMin" not in observation
        assert "pipeLoadPercent" not in observation
        json.dumps(observation, ensure_ascii=False)
        print(f"PASS {status} POST /api/v1/telemetry/observations")

        if websocket_client is not None:
            updated = json.loads(websocket_client.recv())
            assert updated["type"] == "sensor.updated"
            assert updated["payload"]["sensorId"] == "SSZJ-NODE-001"
            assert updated["payload"]["waterDetected"] is True
            assert "receivedAt" in updated["payload"]
            json.dumps(updated, ensure_ascii=False)
            print("PASS WS sensor.updated")
        status, sensor = request("/api/v1/sensors/SSZJ-NODE-001")
        assert status == 200, (status, sensor)
        assert sensor["sensorId"] == "SSZJ-NODE-001"
        assert sensor["siteId"] == "SITE-RML-BJDD"
        assert sensor["coordinates"] == {"lat": 31.2297, "lon": 121.4874}
        assert sensor["depthCm"] == 28.6
        assert sensor["sequence"] == 42
        assert "latestObservation" not in sensor
        json.dumps(sensor, ensure_ascii=False)
        print("PASS 200 GET /api/v1/sensors/SSZJ-NODE-001 SensorState")

        status, points = request("/api/v1/flood-points")
        assert status == 200
        first_projection = next(point for point in points if point["id"] == "FP-001")
        assert first_projection["depthCm"] == 28.6
        assert first_projection["riskLevel"] == "HIGH"
        assert first_projection["trend"] == "UP"
        status, event = request("/api/v1/flood-events/FP202506010024")
        assert status == 200
        assert event["currentDepthCm"] == 28.6
        assert event["riskLevel"] == "HIGH"
        assert event["riseRateCmMin"] == 1.8
        assert event["pipeLoadPercent"] == 91
        print("PASS projection at 28.6cm with risk fields preserved")

        simulator = subprocess.run(
            [
                sys.executable,
                "tools/telemetry_simulator.py",
                "--base-url",
                BASE_URL,
                "--no-wait",
            ],
            cwd=Path(__file__).resolve().parent,
            capture_output=True,
            text=True,
        )
        assert simulator.returncode == 0, (simulator.stdout, simulator.stderr)
        print("PASS telemetry_simulator.py --no-wait")

        status, final_sensor = request("/api/v1/sensors/SSZJ-NODE-001")
        assert status == 200
        assert final_sensor["depthMm"] == 350
        assert final_sensor["depthCm"] == 35.0
        assert final_sensor["waterDetected"] is True
        assert final_sensor["transport"] == "SIMULATOR"
        json.dumps(final_sensor, ensure_ascii=False)

        status, points = request("/api/v1/flood-points")
        assert status == 200
        final_projection = next(point for point in points if point["id"] == "FP-001")
        assert final_projection["depthCm"] == 35.0
        assert final_projection["riskLevel"] == "HIGH"
        assert final_projection["trend"] == "UP"
        status, event = request("/api/v1/flood-events/FP202506010024")
        assert status == 200
        assert event["currentDepthCm"] == 35.0
        assert event["riskLevel"] == "HIGH"
        assert event["riseRateCmMin"] == 1.8
        assert event["pipeLoadPercent"] == 91
        print("PASS simulator final 35.0cm projection with risk fields preserved")

        if websocket_client is not None:
            final_updates = [json.loads(websocket_client.recv()) for _ in range(8)]
            assert final_updates[-1]["type"] == "sensor.updated"
            assert final_updates[-1]["payload"]["depthCm"] == 35.0
            assert final_updates[-1]["payload"]["receivedAt"]
            print("PASS WS final sensor.updated depthCm=35.0")

        unknown_request = dict(observation_request)
        unknown_request["sensorId"] = "UNKNOWN"
        status, payload = request(
            "/api/v1/telemetry/observations",
            method="POST",
            payload=unknown_request,
        )
        assert status == 404, (status, payload)
        assert isinstance(payload, dict) and payload.get("detail", {}).get("code") == "NOT_FOUND"
        print("PASS 404 POST unknown sensor")

        invalid_request = dict(observation_request)
        invalid_request["depthMm"] = -1
        status, payload = request(
            "/api/v1/telemetry/observations",
            method="POST",
            payload=invalid_request,
        )
        assert status == 422, (status, payload)
        assert isinstance(payload, dict) and "detail" in payload
        json.dumps(payload, ensure_ascii=False)
        print("PASS 422 POST invalid depthMm")

        for path in [
            "/api/v1/sensors/UNKNOWN",
            "/api/v1/flood-events/UNKNOWN",
            "/api/v1/flood-events/UNKNOWN/forecast",
            "/api/v1/flood-events/UNKNOWN/analysis",
            "/api/v1/scenarios/UNKNOWN/timeline",
        ]:
            status, payload = request(path)
            assert status == 404, (path, status, payload)
            assert isinstance(payload, dict) and payload.get("detail", {}).get("code") == "NOT_FOUND"
            json.dumps(payload, ensure_ascii=False)
            print(f"PASS 404 {path}")
    finally:
        if websocket_client is not None:
            websocket_client.close()
        process.terminate()
        process.wait(timeout=5)

    print("smoke: PASS")


if __name__ == "__main__":
    main()
