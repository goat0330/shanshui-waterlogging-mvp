from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, Request, build_opener

from app.config import load_settings
from app.main import app, repository, sensor_repository
from app.shanghai_water import ShanghaiWaterAdapter, ShanghaiWaterError
from app.vision_depth import VisionDepthAdapter, VisionDepthError, project_vision_decision

try:
    import websocket
except ImportError:
    websocket = None


PORT = int(os.environ.get("SMOKE_PORT", "8765"))
BASE_URL = f"http://127.0.0.1:{PORT}"
LOCAL_OPENER = build_opener(ProxyHandler({}))


class QuietImageHandler(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        return

    def do_GET(self) -> None:
        if self.path == "/html":
            body = b"<html><body>not an image</body></html>"
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path == "/unavailable":
            self.send_response(503)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            return
        if self.path == "/redirect-private":
            port = self.server.server_address[1]
            self.send_response(302)
            self.send_header("Location", f"http://127.0.0.1:{port}/flood_person.jpg")
            self.end_headers()
            return
        super().do_GET()


def request(
    path: str,
    method: str = "GET",
    payload: dict[str, object] | None = None,
    timeout: float = 3,
) -> tuple[int, object]:
    headers = {"Accept": "application/json"}
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    try:
        with LOCAL_OPENER.open(
            Request(f"{BASE_URL}{path}", data=data, headers=headers, method=method),
            timeout=timeout,
        ) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except HTTPError as error:
        return error.code, json.loads(error.read().decode("utf-8"))


def multipart_request(
    path: str,
    filename: str,
    content: bytes,
    content_type: str,
    image_id: str | None = None,
) -> tuple[int, object]:
    boundary = "----CodexVisionDepthBoundary"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: {content_type}\r\n\r\n"
    ).encode("utf-8") + content + b"\r\n"
    if image_id is not None:
        body += (
            f"--{boundary}\r\n"
            'Content-Disposition: form-data; name="imageId"\r\n\r\n'
            f"{image_id}\r\n"
        ).encode("utf-8")
    body += f"--{boundary}--\r\n".encode("utf-8")
    headers = {
        "Accept": "application/json",
        "Content-Type": f"multipart/form-data; boundary={boundary}",
    }
    try:
        with LOCAL_OPENER.open(
            Request(f"{BASE_URL}{path}", data=body, headers=headers, method="POST"),
            timeout=45,
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
    assert settings.shanghai_water_timeout_seconds > 0
    assert settings.shanghai_water_cache_ttl_seconds > 0
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
    vision_paths = {
        "/api/v1/vision-depth/analyze/upload",
        "/api/v1/vision-depth/analyze/url",
    }
    spec = app.openapi()
    assert set(spec["paths"]) == formal_paths | telemetry_paths | vision_paths
    assert "/api/v1/external/shanghai-water" not in spec["paths"]
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
    flood_point_schema = spec["components"]["schemas"]["FloodPoint"]
    assert "eventId" in flood_point_schema["properties"]
    assert "sensorId" in flood_point_schema["properties"]
    assert "eventId" not in flood_point_schema["required"]
    assert "sensorId" not in flood_point_schema["required"]
    assert {"type": "null"} in flood_point_schema["properties"]["eventId"]["anyOf"]
    assert {"type": "null"} in flood_point_schema["properties"]["sensorId"]["anyOf"]
    overview_schema = spec["components"]["schemas"]["DashboardOverview"]
    assert "waterloggingSituation" not in overview_schema["required"]
    assert overview_schema["properties"]["waterloggingSituation"]["anyOf"][-1] == {"type": "null"}
    situation_schema = spec["components"]["schemas"]["WaterloggingSituation"]
    assert set(situation_schema["required"]) == {
        "totalEvents",
        "changeVsHour",
        "disposition",
        "topDistricts",
        "metrics",
        "source",
    }
    assert situation_schema["additionalProperties"] is False
    assert set(spec["components"]["schemas"]["WaterloggingDisposition"]["required"]) == {
        "pending",
        "handling",
        "relieved",
    }
    assert set(spec["components"]["schemas"]["WaterloggingMetrics"]["required"]) == {
        "maxDepthCm",
        "avgDepthCm",
        "avgResponseMinutes",
        "newToday",
    }
    assert spec["paths"]["/api/v1/vision-depth/analyze/upload"]["post"]["operationId"] == "analyzeVisionDepthUpload"
    assert spec["paths"]["/api/v1/vision-depth/analyze/url"]["post"]["operationId"] == "analyzeVisionDepthUrl"
    upload_request = spec["paths"]["/api/v1/vision-depth/analyze/upload"]["post"]["requestBody"]
    assert upload_request["content"]["multipart/form-data"]["schema"] == {
        "$ref": "#/components/schemas/VisionDepthUploadRequest"
    }
    assert set(spec["components"]["schemas"]["VisionDepthUploadRequest"]["required"]) == {"file"}
    vision_schema = spec["components"]["schemas"]["VisionDepthObservation"]
    assert set(vision_schema["required"]) == {
        "imageId",
        "source",
        "provenance",
        "floodDetected",
        "depth",
        "method",
        "referenceObjects",
        "waterMaskPath",
        "quality",
        "qualityFlags",
        "model",
        "synthetic",
    }
    assert vision_schema["additionalProperties"] is False
    assert spec["components"]["schemas"]["VisionDepthSourceType"]["enum"] == ["url", "local"]
    provenance_schema = spec["components"]["schemas"]["VisionDepthProvenance"]
    assert set(provenance_schema["required"]) == {
        "sourceType",
        "sourceId",
        "observedAt",
        "licenseReview",
        "runtimePolicy",
    }
    assert provenance_schema["additionalProperties"] is False
    assert spec["components"]["schemas"]["VisionDepthProvenanceSourceType"]["enum"] == [
        "VISION_IMAGE",
        "VISION_VIDEO",
    ]
    assert spec["components"]["schemas"]["VisionDepthLicenseReview"]["enum"] == [
        "approved",
        "pending",
        "not_required",
    ]
    assert spec["components"]["schemas"]["VisionDepthRuntimePolicy"]["enum"] == [
        "research_mvp",
        "production",
    ]
    decision_schema = spec["components"]["schemas"]["VisionDecisionProjection"]
    assert set(decision_schema["required"]) == {
        "floodDetected",
        "decisionDepthCm",
        "trafficStatus",
        "recommendation",
    }
    assert decision_schema["additionalProperties"] is False
    assert spec["components"]["schemas"]["VisionDecisionTrafficStatus"]["enum"] == [
        "NORMAL",
        "CAUTION",
        "NOT_RECOMMENDED",
        "PROHIBITED",
    ]
    assert {"$ref": "#/components/schemas/VisionDecisionProjection"} in vision_schema["properties"]["decision"]["anyOf"]
    assert provenance_schema["properties"]["sourceId"]["minLength"] == 1
    assert {"type": "null"} in provenance_schema["properties"]["observedAt"]["anyOf"]
    assert spec["components"]["schemas"]["VisionDepthMethod"]["enum"] == [
        "VISUAL_RANGE",
        "NO_REFERENCE",
        "PERSON_REFERENCE",
        "VEHICLE_REFERENCE",
        "TRAFFIC_SIGN_REFERENCE",
        "FIXED_CAMERA_REFERENCE",
    ]
    assert spec["components"]["schemas"]["VisionDepthQuality"]["enum"] == ["LOW", "MEDIUM", "HIGH", "REJECT"]
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
    for private_url in [
        "http://127.0.0.1/image.jpg",
        "http://localhost/image.jpg",
        "http://169.254.169.254/latest/meta-data",
    ]:
        try:
            VisionDepthAdapter._validate_public_url(private_url)
        except VisionDepthError as exc:
            assert exc.status_code == 400 and exc.code == "VISION_PRIVATE_URL", (private_url, exc.detail())
        else:
            raise AssertionError(f"private URL was not blocked: {private_url}")
    print("PASS VisionDepth private-target/SSRF literal and localhost guards")
    for depth_cm, expected_status in [
        (0, "NORMAL"),
        (10, "CAUTION"),
        (20, "NOT_RECOMMENDED"),
        (30, "PROHIBITED"),
        (50, "PROHIBITED"),
    ]:
        decision = project_vision_decision(True, depth_cm)
        assert decision.trafficStatus.value == expected_status, (depth_cm, decision)
    dry_video_fixture = backend_dir.parent / "media" / "artifacts" / "video-smoke-synthetic.json"
    video_frame = json.loads(dry_video_fixture.read_text(encoding="utf-8"))["frames"][0]["observation"]
    video_decision = project_vision_decision(
        flood_detected=video_frame["floodDetected"],
        estimated_depth_cm=video_frame["depth"].get("estimatedDepthCm"),
        approximate_depth_cm=video_frame["depth"].get("approximateDepthCm"),
        range_cm=video_frame["depth"].get("rangeCm"),
    )
    assert video_decision.model_dump(mode="json") == {
        "floodDetected": False,
        "decisionDepthCm": 0.0,
        "trafficStatus": "NORMAL",
        "recommendation": "正常通行",
    }
    print("PASS Vision image/video decision projection thresholds and video sample")
    print("PASS OpenAPI formal paths/enums, VisionDepth Contract shape, SensorRegistryEntry, and adapter fixture validation")

    source_row = {
        "STATIONID": "S-001",
        "STATIONNAME": "测试站",
        "DATETIME": "2026-08-25 12:00:00",
        "XX2000": "121.4874",
        "YY2000": "31.2297",
    }
    source_rows = {
        "SSYLMore": [{**source_row, "RAINVALUE": "12.3"}],
        "JSJCMore": [{**source_row, "JISHUISTATUS": "8.5"}],
        "SSSW": [{**source_row, "OUTWATER": "2.75"}],
        "YJSW": [{**source_row, "YBCW": "2.90"}],
    }
    adapter = ShanghaiWaterAdapter(cache_ttl_seconds=60)
    with patch.object(adapter, "_fetch_list", side_effect=lambda dataset_type: source_rows[dataset_type]):
        snapshot = adapter.fetch(allow_partial=False)
        assert snapshot.sourceStatus == "ok"
        assert snapshot.receivedAt >= snapshot.fetchedAt
        assert all(item.status.value == "ok" for item in snapshot.sourceHealth.values())
        rainfall_item = snapshot.rainfall[0]
        assert rainfall_item.observedAt.isoformat() == "2026-08-25T12:00:00+08:00"
        assert rainfall_item.receivedAt.tzinfo is not None
        assert rainfall_item.sourceId == rainfall_item.stationId
        assert rainfall_item.provider == ShanghaiWaterAdapter.SOURCE
        assert rainfall_item.rawSource.endswith("type=SSYLMore")
        cached_snapshot = adapter.fetch(allow_partial=False)
        assert cached_snapshot.cacheHit is True
    print("PASS Shanghai Water per-record provenance, Shanghai timezone, and TTL cache")

    malformed_rows = {**source_rows, "YJSW": [{**source_row, "DATETIME": "2026-08-25 12:00:00"}]}
    partial_adapter = ShanghaiWaterAdapter(cache_ttl_seconds=60)
    with patch.object(partial_adapter, "_fetch_list", side_effect=lambda dataset_type: malformed_rows[dataset_type]):
        partial_snapshot = partial_adapter.fetch(allow_partial=True)
        assert partial_snapshot.sourceStatus == "partial"
        assert partial_snapshot.sourceHealth["YJSW"].status.value == "schema_mismatch"
        assert partial_snapshot.sourceHealth["YJSW"].errorCode == "SHANGHAI_WATER_SCHEMA_MISMATCH"
    unavailable_adapter = ShanghaiWaterAdapter(cache_ttl_seconds=60)

    def fail_one_source(dataset_type: str) -> list[dict[str, object]]:
        if dataset_type == "SSSW":
            raise ShanghaiWaterError("SHANGHAI_WATER_FETCH_FAILED", "test timeout")
        return source_rows[dataset_type]

    with patch.object(unavailable_adapter, "_fetch_list", side_effect=fail_one_source):
        unavailable_snapshot = unavailable_adapter.fetch(allow_partial=True)
        assert unavailable_snapshot.sourceStatus == "partial"
        assert unavailable_snapshot.sourceHealth["SSSW"].status.value == "unavailable"
        assert unavailable_snapshot.sourceHealth["SSSW"].errorCode == "SHANGHAI_WATER_FETCH_FAILED"
    strict_adapter = ShanghaiWaterAdapter(cache_ttl_seconds=60)
    with patch.object(strict_adapter, "_fetch_list", side_effect=lambda dataset_type: malformed_rows[dataset_type]):
        try:
            strict_adapter.fetch(allow_partial=False)
        except ShanghaiWaterError as exc:
            assert exc.code == "SHANGHAI_WATER_SCHEMA_MISMATCH"
        else:
            raise AssertionError("real-mode strict source failure was not raised")
    print("PASS Shanghai Water schema gate, hybrid partial health, and real strict failure")

    websocket_client = None
    vision_server = None
    vision_thread = None
    process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(PORT)],
        cwd=Path(__file__).resolve().parent,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        wait_until_ready()
        vision_input = backend_dir.parent / "vision" / "artifacts" / "smoke_inputs" / "flood_person.jpg"
        assert vision_input.is_file(), vision_input
        vision_server = ThreadingHTTPServer(
            ("127.0.0.1", 0),
            partial(QuietImageHandler, directory=str(vision_input.parent)),
        )
        vision_thread = threading.Thread(target=vision_server.serve_forever, daemon=True)
        vision_thread.start()
        vision_base_url = f"http://127.0.0.1:{vision_server.server_port}"
        local_image_url = f"{vision_base_url}/{vision_input.name}"
        with patch.object(VisionDepthAdapter, "_validate_public_url", return_value=None):
            direct_url_observation = VisionDepthAdapter().analyze_url(local_image_url, "IMG-RC2-DIRECT-URL")
        assert direct_url_observation.source.type.value == "url"
        assert direct_url_observation.imageId == "IMG-RC2-DIRECT-URL"
        assert direct_url_observation.provenance.model_dump(mode="json") == {
            "sourceType": "VISION_IMAGE",
            "sourceId": "IMG-RC2-DIRECT-URL",
            "observedAt": None,
            "licenseReview": "pending",
            "runtimePolicy": "research_mvp",
        }
        assert direct_url_observation.decision is not None
        assert direct_url_observation.decision.trafficStatus.value == "NOT_RECOMMENDED"
        assert direct_url_observation.decision.decisionDepthCm == 25.4
        with patch.object(VisionDepthAdapter, "_validate_public_url", return_value=None):
            try:
                VisionDepthAdapter._download_public_url(f"{vision_base_url}/html")
            except VisionDepthError as exc:
                assert exc.status_code == 400 and exc.code == "VISION_INVALID_MEDIA"
            else:
                raise AssertionError("HTML media was not rejected")
            try:
                VisionDepthAdapter._download_public_url(f"{vision_base_url}/unavailable")
            except VisionDepthError as exc:
                assert exc.status_code == 502 and exc.code == "VISION_FETCH_FAILED"
            else:
                raise AssertionError("unavailable media was not mapped")
        with patch.object(
            VisionDepthAdapter,
            "_validate_public_url",
            side_effect=[None, VisionDepthError(400, "VISION_PRIVATE_URL", "redirect target blocked")],
        ):
            try:
                VisionDepthAdapter._download_public_url(f"{vision_base_url}/redirect-private")
            except VisionDepthError as exc:
                assert exc.status_code == 400 and exc.code == "VISION_PRIVATE_URL"
            else:
                raise AssertionError("private redirect target was not blocked")
        print("PASS VisionDepth secure URL media, unavailable, and redirect guards")
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

        if settings.data_mode == "fixture":
            status, external_snapshot = request("/api/v1/external/shanghai-water", timeout=20)
            assert status == 503, (status, external_snapshot)
            assert external_snapshot["detail"]["code"] == "REAL_SOURCE_DISABLED"
            print("PASS Shanghai Water adapter disabled in fixture mode with explicit 503")
        elif settings.data_mode == "real":
            status, external_snapshot = request("/api/v1/external/shanghai-water", timeout=20)
            if status == 200:
                assert external_snapshot["sourceStatus"] == "ok"
                assert all(item["status"] == "ok" for item in external_snapshot["sourceHealth"].values())
                print("PASS Shanghai Water real mode with all four sources healthy")
            else:
                assert status == 503, (status, external_snapshot)
                assert external_snapshot["detail"]["code"] in {
                    "SHANGHAI_WATER_FETCH_FAILED",
                    "SHANGHAI_WATER_SCHEMA_MISMATCH",
                    "SHANGHAI_WATER_EMPTY",
                    "SHANGHAI_WATER_UNAVAILABLE",
                }
                print(
                    "PASS Shanghai Water real mode rejected incomplete source set with explicit 503 "
                    f"code={external_snapshot['detail']['code']}"
                )
        elif os.environ.get("SMOKE_SHANGHAI_WATER") == "1":
            status, external_snapshot = request("/api/v1/external/shanghai-water", timeout=20)
            assert status == 200, (status, external_snapshot)
            assert external_snapshot["source"] == "SHANGHAI_WATER_BUREAU_PUBLIC"
            assert external_snapshot["sourceStatus"] in {"ok", "partial"}
            assert set(external_snapshot["sourceHealth"]) == {"SSYLMore", "JSJCMore", "SSSW", "YJSW"}
            assert external_snapshot["coordinateReference"] == "SOURCE_REPORTED_XX2000_YY2000"
            assert external_snapshot["rainfall"]
            assert external_snapshot["ponding"]
            assert external_snapshot["waterLevels"]
            assert all(item["rainfallValue"] >= 0 for item in external_snapshot["rainfall"])
            assert all(item["depthCm"] >= 0 for item in external_snapshot["ponding"])
            assert all(item["outWaterM"] >= 0 for item in external_snapshot["waterLevels"])
            assert all(item["synthetic"] is False for item in external_snapshot["rainfall"])
            assert all(item["sourceId"] == item["stationId"] for item in external_snapshot["rainfall"])
            assert all("+08:00" in item["observedAt"] or "Z" in item["observedAt"] for item in external_snapshot["rainfall"])
            json.dumps(external_snapshot, ensure_ascii=False)
            print(
                "PASS Shanghai Water live source "
                f"rainfall={len(external_snapshot['rainfall'])} "
                f"ponding={len(external_snapshot['ponding'])} "
                f"waterLevels={len(external_snapshot['waterLevels'])}"
            )
        else:
            print("SKIP Shanghai Water live fetch (set DATA_MODE=hybrid and SMOKE_SHANGHAI_WATER=1)")

        status, overview = request("/api/v1/dashboard/overview")
        assert status == 200
        situation = overview["waterloggingSituation"]
        assert situation["totalEvents"] == 1
        assert situation["changeVsHour"] == 108.0
        assert situation["disposition"] == {"pending": 0, "handling": 1, "relieved": 0}
        assert situation["topDistricts"] == [{"district": "黄浦区", "eventCount": 1}]
        assert situation["metrics"] == {
            "maxDepthCm": 28.6,
            "avgDepthCm": 19.4,
            "avgResponseMinutes": 32.4,
            "newToday": 1,
        }
        assert situation["source"] == "FIXTURE_DERIVED"
        json.dumps(overview, ensure_ascii=False)
        print("PASS dashboard waterloggingSituation fixture-derived summary")

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
        assert len(points) == 5
        points_by_id = {point["id"]: point for point in points}
        assert set(points_by_id) == {"FP-001", "FP-002", "FP-003", "FP-004", "FP-005"}
        assert points_by_id["FP-001"]["eventId"] == "FP202506010024"
        assert points_by_id["FP-001"]["sensorId"] == "SSZJ-NODE-001"
        for flood_point_id in ["FP-002", "FP-003", "FP-004", "FP-005"]:
            assert points_by_id[flood_point_id]["eventId"] is None
            assert points_by_id[flood_point_id]["sensorId"] is None
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

        vision_bytes = vision_input.read_bytes()
        status, upload_observation = multipart_request(
            "/api/v1/vision-depth/analyze/upload",
            vision_input.name,
            vision_bytes,
            "image/jpeg",
            "IMG-RC11-UPLOAD",
        )
        assert status == 200, (status, upload_observation)
        assert set(upload_observation) == {
            "imageId",
            "source",
            "provenance",
            "floodDetected",
            "depth",
            "method",
            "referenceObjects",
            "waterMaskPath",
            "quality",
            "qualityFlags",
            "model",
            "synthetic",
            "decision",
        }
        assert upload_observation["imageId"] == "IMG-RC11-UPLOAD"
        assert upload_observation["source"]["type"] == "local"
        assert upload_observation["depth"]["estimatedDepthCm"] == 25.4
        assert upload_observation["depth"]["approximateDepthCm"] is None
        assert upload_observation["provenance"] == {
            "sourceType": "VISION_IMAGE",
            "sourceId": "IMG-RC11-UPLOAD",
            "observedAt": None,
            "licenseReview": "not_required",
            "runtimePolicy": "research_mvp",
        }
        assert upload_observation["decision"] == {
            "floodDetected": True,
            "decisionDepthCm": 25.4,
            "trafficStatus": "NOT_RECOMMENDED",
            "recommendation": "不建议通行",
        }
        assert "provenance" not in upload_observation["model"]
        assert upload_observation["synthetic"] is False
        json.dumps(upload_observation, ensure_ascii=False)
        print("PASS 200 VisionDepth multipart upload and Contract response")

        mask_path = upload_observation["waterMaskPath"]
        assert mask_path.startswith("/api/v1/vision-depth/artifacts/")
        with LOCAL_OPENER.open(
            Request(f"{BASE_URL}{mask_path}", headers={"Accept": "image/png"}),
            timeout=3,
        ) as mask_response:
            mask_bytes = mask_response.read()
            assert mask_response.status == 200
            assert mask_response.headers.get_content_type() == "image/png"
            assert mask_bytes.startswith(b"\x89PNG\r\n\x1a\n")
        print("PASS VisionDepth water mask browser artifact route")

        status, sensor_after_upload = request("/api/v1/sensors/SSZJ-NODE-001")
        assert status == 200
        assert sensor_after_upload == sensor
        print("PASS VisionDepth upload preserved current SensorState")

        status, url_observation = request(
            "/api/v1/vision-depth/analyze/url",
            method="POST",
            payload={"url": local_image_url, "imageId": "IMG-RC2-PRIVATE-URL"},
        )
        assert status == 400, (status, url_observation)
        assert url_observation["detail"]["code"] == "VISION_PRIVATE_URL"
        print("PASS URL endpoint blocks private target before fetch")

        status, payload = multipart_request(
            "/api/v1/vision-depth/analyze/upload",
            "not-an-image.html",
            b"<html><body>not an image</body></html>",
            "text/html",
            "IMG-RC11-BAD-MIME",
        )
        assert status == 415, (status, payload)
        assert payload["detail"]["code"] == "VISION_UNSUPPORTED_MEDIA_TYPE"
        print("PASS 415 VisionDepth unsupported upload MIME")

        status, payload = multipart_request(
            "/api/v1/vision-depth/analyze/upload",
            "not-an-image.svg",
            b"<svg xmlns='http://www.w3.org/2000/svg'></svg>",
            "image/svg+xml",
            "IMG-RC2-BAD-SVG",
        )
        assert status == 415, (status, payload)
        assert payload["detail"]["code"] == "VISION_UNSUPPORTED_MEDIA_TYPE"
        print("PASS 415 VisionDepth SVG rejection")

        status, payload = multipart_request(
            "/api/v1/vision-depth/analyze/upload",
            "too-large.jpg",
            b"0" * (15 * 1024 * 1024 + 1),
            "image/jpeg",
            "IMG-RC11-TOO-LARGE",
        )
        assert status == 413, (status, payload)
        assert payload["detail"]["code"] == "VISION_IMAGE_TOO_LARGE"
        print("PASS 413 VisionDepth upload size limit")

        status, payload = request(
            "/api/v1/vision-depth/analyze/url",
            method="POST",
            payload={"url": "ftp://127.0.0.1/not-an-image", "imageId": "IMG-RC11-BAD-URL"},
        )
        assert status == 400, (status, payload)
        assert payload["detail"]["code"] == "VISION_INVALID_URL"

        status, payload = request(
            "/api/v1/vision-depth/analyze/url",
            method="POST",
            payload={"url": "http://169.254.169.254/latest/meta-data", "imageId": "IMG-RC2-METADATA"},
        )
        assert status == 400, (status, payload)
        assert payload["detail"]["code"] == "VISION_PRIVATE_URL"
        print("PASS VisionDepth API 400/415 private URL and invalid URL errors")

        status, payload = request(
            "/api/v1/vision-depth/analyze/url",
            method="POST",
            payload={},
        )
        assert status == 422, (status, payload)
        assert isinstance(payload, dict) and "detail" in payload
        json.dumps(payload, ensure_ascii=False)
        print("PASS VisionDepth request boundary and JSON error serialization")

        def run_concurrent_vision(image_id: str) -> tuple[int, object]:
            return request(
                "/api/v1/vision-depth/analyze/url",
                method="POST",
                payload={"url": local_image_url, "imageId": image_id},
            )

        with ThreadPoolExecutor(max_workers=2) as executor:
            concurrent_results = list(executor.map(run_concurrent_vision, ["IMG-RC2-CONCURRENT-1", "IMG-RC2-CONCURRENT-2"]))
        assert all(status_code == 400 for status_code, _ in concurrent_results), concurrent_results
        assert all(payload["detail"]["code"] == "VISION_PRIVATE_URL" for _, payload in concurrent_results)
        print("PASS VisionDepth two-request concurrency and SSRF boundary")

        status, sensor_after_vision = request("/api/v1/sensors/SSZJ-NODE-001")
        assert status == 200
        assert sensor_after_vision["depthCm"] == 28.6
        assert sensor_after_vision["sequence"] == 42
        status, points_after_vision = request("/api/v1/flood-points")
        assert status == 200
        assert next(point for point in points_after_vision if point["id"] == "FP-001")["depthCm"] == 28.6
        status, event_after_vision = request("/api/v1/flood-events/FP202506010024")
        assert status == 200
        assert event_after_vision["currentDepthCm"] == 28.6
        assert event_after_vision["riskLevel"] == "HIGH"
        print("PASS VisionDepth evidence did not overwrite SensorState or flood projection")

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
        if vision_server is not None:
            vision_server.shutdown()
            vision_server.server_close()
        if vision_thread is not None:
            vision_thread.join(timeout=2)
        process.terminate()
        process.wait(timeout=5)

    print("smoke: PASS")


if __name__ == "__main__":
    main()
