from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.cma_source import CmaSourceAdapter
from app.shanghai_water import ShanghaiWaterAdapter


def main() -> None:
    adapter = ShanghaiWaterAdapter(timeout_seconds=1, cache_ttl_seconds=1)
    samples = {
        "SSYLMore": [{
            "STATIONID": "R-1", "STATIONNAME": "雨量站", "RAINVALUE": "12.5",
            "DATETIME": "2026-08-26 09:30:00", "XX2000": "121.48", "YY2000": "31.23",
        }],
        "JSJCMore": [{
            "STATIONID": "P-1", "STATIONNAME": "积水点", "JISHUISTATUS": "8.0",
            "DATETIME": "2026-08-26 09:30:00", "XX2000": "121.49", "YY2000": "31.24",
        }],
        # Alias fields + signed water level prove source-local normalization.
        "SSSW": [
            {
                "STCD": "W-1", "STNM": "水位站", "WATER_LEVEL": "-0.12",
                "TM": "2026/08/26 09:30:00", "LON": "121.50", "LAT": "31.25",
            },
            {"STATIONID": "BROKEN"},
        ],
        # Optional forecast may be empty without making strict real observations fail.
        "YJSW": [],
    }
    adapter._fetch_list = lambda dataset_type: samples[dataset_type]  # type: ignore[method-assign]
    snapshot = adapter.fetch(allow_partial=False)
    assert len(snapshot.rainfall) == 1
    assert len(snapshot.ponding) == 1
    assert len(snapshot.waterLevels) == 1
    assert snapshot.waterLevels[0].outWaterM == -0.12
    assert snapshot.sourceHealth["SSSW"].status.value == "ok"
    assert "skipped" in (snapshot.sourceHealth["SSSW"].fallbackReason or "")
    assert snapshot.coordinateReference == "SOURCE_REPORTED_XX2000_YY2000"
    print("PASS Shanghai Water normalization / signed level / row-skip strict mode")

    warning_payload = {
        "warnings": [{
            "identifier": "WARN-1", "event": "暴雨预警", "severity": "橙色",
            "sent": "2026-08-26T01:30:00Z", "areaDesc": "上海市",
        }]
    }
    warnings = CmaSourceAdapter.parse_generic_warnings(warning_payload)
    assert len(warnings) == 1 and warnings[0].sourceId == "WARN-1"

    nowcast_payload = {
        "frames": [{
            "id": "RADAR-30", "offsetMinutes": 30,
            "validAt": "2026-08-26T02:00:00Z",
            "rasterUrl": "https://example.invalid/radar-30.png",
            "mediaType": "image/png", "crs": "EPSG:4326",
            "bbox": [120.8, 30.6, 122.2, 31.9],
        }]
    }
    frames = CmaSourceAdapter.parse_generic_nowcast(nowcast_payload)
    assert len(frames) == 1 and frames[0].renderableInCesium is True
    print("PASS CMA warning + georeferenced nowcast metadata parser")

    history = json.loads((ROOT / "data" / "historical-cases.json").read_text(encoding="utf-8"))
    records = history["records"]
    assert len(records) == 8
    assert all(item["mvpReviewStatus"] == "VERIFIED_FOR_MVP" for item in records)
    media = [item["media"] for item in records if item.get("media")]
    assert len(media) == 2
    assert all(item["mvpUseStatus"] == "APPROVED_LOCAL_MVP" for item in media)
    assert all(item.get("sensorId") is None for item in records)
    print("PASS 8 historical cases + canonical CASE_SOURCE_MEDIA MVP gate")

    components = (ROOT / "frontend" / "src" / "components.tsx").read_text(encoding="utf-8")
    assert "权限待用户确认" not in components
    assert "local_mvp_allowed · external_redistribution_pending" in components
    app = (ROOT / "frontend" / "src" / "App.tsx").read_text(encoding="utf-8")
    assert "API DEGRADED · PARTIAL FIXTURE FALLBACK" in app
    assert "selectedHistoricalCase ? (" in app
    assert "<HistoricalMediaPanel historicalCase={selectedHistoricalCase}" in app
    assert ") : selectedEventKey === 'REALTIME_EVENT' ? (" in app
    api_client = (ROOT / "frontend" / "src" / "services" / "apiClient.ts").read_text(encoding="utf-8")
    assert "http://127.0.0.1:8000').replace" not in api_client
    assert "configuredApiBase" in api_client
    print("PASS frontend evidence wording + degraded API routing checks")

    registry = (ROOT / "backend" / "visiondepth_v2" / "third_party_registry.yaml").read_text(encoding="utf-8")
    assert "allowed_in_mvp: false" not in registry
    assert "mvp_use_scope: local_research_only" in registry
    manifest = (ROOT / "docs" / "06_DELIVERY_MANIFEST.md").read_text(encoding="utf-8")
    assert "0.648314" in manifest and "MODEL_UPGRADE=NOT_VERIFIED" not in manifest
    metrics = json.loads((ROOT / "vision" / "artifacts" / "urban-flood-segmentation-metrics.json").read_text(encoding="utf-8"))
    assert metrics["status"] == "PASS"
    assert metrics["mvpReviewStatus"] == "VERIFIED_FOR_RESEARCH_MVP"
    assert metrics["source"]["declaredLicense"] == "CC BY 4.0"
    assert metrics["source"]["rightsReview"] != "DEFERRED_TO_USER"
    print("PASS evidence/license/current-state reconciliation")

    print("PASS leanguard repair smoke")


if __name__ == "__main__":
    main()
