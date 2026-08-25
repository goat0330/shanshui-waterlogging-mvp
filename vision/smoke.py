"""Three-image smoke for the local VisionDepth V1 baseline."""

from __future__ import annotations

import json
from pathlib import Path

from .decision import project_decision
from .pipeline import run_pipeline
from .schema import validate_observation


ROOT = Path(__file__).resolve().parent
ARTIFACTS = ROOT / "artifacts"
SAMPLES = [
    {
        "image_id": "IMG-00001",
        "name": "flood_person",
        "path": ARTIFACTS / "smoke_inputs" / "flood_person.jpg",
        "expected": "flood_with_reference",
    },
    {
        "image_id": "IMG-00002",
        "name": "flood_no_reference",
        "path": ARTIFACTS / "smoke_inputs" / "flood_no_reference.jpg",
        "expected": "flood_without_reliable_reference",
    },
    {
        "image_id": "IMG-00003",
        "name": "dry_street",
        "path": ARTIFACTS / "smoke_inputs" / "dry_street.jpg",
        "expected": "non_flood",
    },
]


def main() -> int:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    results = []
    for sample in SAMPLES:
        if not sample["path"].is_file():
            raise FileNotFoundError(f"missing smoke image: {sample['path']}")
        output = ARTIFACTS / f"{sample['image_id']}.json"
        result = run_pipeline(str(sample["path"]), output, sample["image_id"])
        validate_observation(result)
        reloaded = json.loads(output.read_text(encoding="utf-8"))
        validate_observation(reloaded)
        if not Path(output.parent / Path(result["waterMaskPath"]).name).is_file():
            raise AssertionError(f"mask not written for {sample['name']}")
        assert 0 <= result["depth"]["confidence"] <= 1
        decision = project_decision(result)
        assert decision["floodDetected"] == result["floodDetected"]
        assert decision["decisionDepthCm"] >= 0
        assert decision["trafficStatus"] in {"NORMAL", "CAUTION", "NOT_RECOMMENDED", "PROHIBITED"}
        if sample["expected"] == "flood_with_reference":
            assert result["floodDetected"], result
            assert result["depth"]["estimatedDepthCm"] is not None, result
        elif sample["expected"] == "flood_without_reliable_reference":
            assert result["floodDetected"], result
            assert result["depth"]["estimatedDepthCm"] is None, result
            if result["depth"]["level"] == 5:
                assert result["depth"]["approximateDepthCm"] is None, result
            else:
                assert result["depth"]["approximateDepthCm"] is not None, result
            assert "NO_REFERENCE" in result["qualityFlags"], result
        else:
            assert not result["floodDetected"], result
            assert result["depth"]["level"] <= 1, result
        results.append(
            {
                "name": sample["name"],
                "expected": sample["expected"],
                "result": result,
                "decision": decision,
            }
        )

    summary = ARTIFACTS / "smoke-summary.json"
    summary.write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"VisionDepth smoke passed: {len(results)} images")
    for item in results:
        result = item["result"]
        print(
            f"- {item['name']}: flood={result['floodDetected']} "
            f"level={result['depth']['level']} estimate={result['depth']['estimatedDepthCm']} "
            f"approximate={result['depth']['approximateDepthCm']} "
            f"decision={item['decision']['decisionDepthCm']} "
            f"traffic={item['decision']['trafficStatus']} "
            f"method={result['method']} confidence={result['depth']['confidence']}"
        )
    print(f"summary={summary.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
