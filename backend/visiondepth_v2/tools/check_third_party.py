"""Block external model use until license review is explicitly approved."""

from __future__ import annotations

from pathlib import Path

import yaml


PACKAGE_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
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
        print("THIRD_PARTY_REVIEW_REQUIRED")
        for item in blocked:
            print(f"- {item.get('name')}: {item.get('license_review', 'missing')}")
        return 2
    print("THIRD_PARTY_CHECK_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
