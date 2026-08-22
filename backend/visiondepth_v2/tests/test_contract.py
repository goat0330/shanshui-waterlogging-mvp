from __future__ import annotations

import sys

import pytest

from src.visiondepth.backends.external_command import ExternalCommandBackend
from src.visiondepth.engine import guard_observation


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
