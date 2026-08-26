"""Keep pending third-party use local-only until review is explicitly approved."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import yaml


PACKAGE_ROOT = Path(__file__).resolve().parents[1]


def _load_runtime_config(config_path: str | Path) -> dict[str, Any]:
    value = yaml.safe_load(Path(config_path).resolve().read_text(encoding="utf-8")) or {}
    return value if isinstance(value, dict) else {}


def _allows_local_research(config: dict[str, Any]) -> bool:
    return (
        config.get("runtime_profile") == "research_mvp"
        and not bool(config.get("redistribution", False))
        and not bool(config.get("external_models_enabled", False))
    )


def _local_mvp_assets(entries: list[dict[str, Any]]) -> list[str]:
    return [
        str(item.get("name"))
        for item in entries
        if item.get("allowed_in_mvp") is True
        and item.get("mvp_scope") == "local_research_video_evidence_only"
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(PACKAGE_ROOT / "configs" / "local.yaml"))
    args = parser.parse_args()
    config = _load_runtime_config(args.config)
    registry_path = PACKAGE_ROOT / "third_party_registry.yaml"
    registry = yaml.safe_load(registry_path.read_text(encoding="utf-8")) or {}
    entries = registry.get("repositories", [])
    blocked = [
        item
        for item in entries
        if item.get("integration") != "reference_only"
        and item.get("license_review") != "approved"
    ]
    if blocked:
        if _allows_local_research(config):
            print("THIRD_PARTY_CHECK_PASS: RESEARCH_MVP_LOCAL_ONLY")
            allowed_assets = _local_mvp_assets(entries)
            if allowed_assets:
                print(f"- local research assets allowed: {', '.join(allowed_assets)}")
            print("- pending entries remain blocked for production/redistribution/external model use")
            return 0
        print("THIRD_PARTY_REVIEW_REQUIRED")
        for item in blocked:
            print(f"- {item.get('name')}: {item.get('license_review', 'missing')}")
        return 2
    print("THIRD_PARTY_CHECK_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
