from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from vision.decision import _traffic_status, project_decision
from vision.depth_estimation import _approximate_depth, _visual_level
from src.visiondepth.backends.external_command import ExternalCommandBackend
from src.visiondepth.engine import guard_observation
from tools.check_third_party import _allows_local_research


def _observation() -> dict[str, object]:
    return {
        "imageId": "IMG-TEST",
        "source": {"type": "local", "value": "frame.png"},
        "floodDetected": True,
        "depth": {
            "level": 2,
            "estimatedDepthCm": 17.0,
            "rangeCm": [10, 20],
            "confidence": 0.8,
        },
        "method": "VEHICLE_REFERENCE",
        "referenceObjects": [{"type": "vehicle", "reliable": True}],
        "waterMaskPath": "IMG-TEST-water-mask.png",
        "quality": "LOW",
        "qualityFlags": [],
        "model": {
            "waterSegmentation": "opencv_baseline",
            "referenceDetection": "opencv_baseline",
            "geometrySupport": "none",
        },
        "synthetic": False,
    }


def test_visual_level_thresholds_and_open_range_are_explainable() -> None:
    scores = (0.20, 0.40, 0.50, 0.70, 0.90)
    assert [_visual_level(SimpleNamespace(score=score)) for score in scores] == [1, 2, 3, 4, 5]
    assert _approximate_depth(4) == 40.0
    assert _approximate_depth(5) is None


def test_decision_projection_uses_evidence_and_frozen_traffic_rules() -> None:
    assert [_traffic_status(value, True) for value in (0, 9.9, 10, 19.9, 20, 29.9, 30, 49.9, 50)] == [
        "NORMAL",
        "NORMAL",
        "CAUTION",
        "CAUTION",
        "NOT_RECOMMENDED",
        "NOT_RECOMMENDED",
        "PROHIBITED",
        "PROHIBITED",
        "PROHIBITED",
    ]
    estimate = project_decision(_observation())
    assert estimate == {
        "floodDetected": True,
        "decisionDepthCm": 17.0,
        "trafficStatus": "CAUTION",
        "recommendation": "CAUTION_PASSAGE",
        "decisionDepthSource": "ESTIMATED_REFERENCE",
    }

    no_reference = _observation()
    no_reference["method"] = "NO_REFERENCE"
    no_reference["depth"] = {
        "level": 5,
        "estimatedDepthCm": None,
        "approximateDepthCm": None,
        "rangeCm": [50, None],
        "confidence": 0.4,
    }
    lower_bound = project_decision(no_reference)
    assert lower_bound["decisionDepthCm"] == 50.0
    assert lower_bound["trafficStatus"] == "PROHIBITED"
    assert lower_bound["recommendation"] == "NO_PASSAGE"
    assert lower_bound["decisionDepthSource"] == "LEVEL_LOWER_BOUND"


def test_uncalibrated_guard_keeps_contract_and_removes_cm() -> None:
    original = _observation()
    guarded = guard_observation(
        original,
        camera_profile={"calibrationStatus": "uncalibrated"},
    )
    assert original["depth"]["estimatedDepthCm"] == 17.0
    assert guarded["depth"]["estimatedDepthCm"] is None
    assert guarded["depth"]["confidence"] <= 0.45
    assert "CAMERA_UNCALIBRATED" in guarded["qualityFlags"]


def test_calibrated_profile_does_not_add_guard_flag() -> None:
    guarded = guard_observation(
        _observation(),
        camera_profile={"calibrationStatus": "calibrated"},
    )
    assert guarded["depth"]["estimatedDepthCm"] == 17.0
    assert "CAMERA_UNCALIBRATED" not in guarded["qualityFlags"]


def test_external_backend_is_license_gated() -> None:
    with pytest.raises(PermissionError, match="THIRD_PARTY_LICENSE_NOT_APPROVED"):
        ExternalCommandBackend(["external-model", "{input}"])


def test_approved_external_backend_expands_paths(tmp_path) -> None:
    metadata_path = tmp_path / "result.json"
    backend = ExternalCommandBackend(
        [
            sys.executable,
            "-c",
            "import sys; from pathlib import Path; Path(sys.argv[1]).write_text('{\"ok\": true}')",
            "{json}",
        ],
        license_approved=True,
    )
    assert backend.run("frame.png", "mask.png", metadata_path) == {"ok": True}


def test_research_profile_does_not_open_production_gate() -> None:
    assert _allows_local_research(
        {
            "runtime_profile": "research_mvp",
            "redistribution": False,
            "external_models_enabled": False,
        }
    )
    assert not _allows_local_research(
        {
            "runtime_profile": "production",
            "redistribution": False,
            "external_models_enabled": False,
        }
    )
    assert not _allows_local_research(
        {
            "runtime_profile": "research_mvp",
            "redistribution": True,
            "external_models_enabled": False,
        }
    )
