from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Iterable


class ForecastAdapter:
    """Small replaceable boundary for Contract-shaped forecast fixtures."""

    source = "DEMO_SYNTHETIC_FIXTURE"
    _expected_time_keys = ("NOW", "PLUS_10", "PLUS_30")

    def __init__(self, fixture_dir: Path, event_ids: Iterable[str]) -> None:
        self.fixture_dir = fixture_dir
        self.event_ids = set(event_ids)
        self.records = self._load_records()

    def _load_records(self) -> dict[str, dict[str, Any]]:
        records: dict[str, dict[str, Any]] = {}
        for path in sorted(self.fixture_dir.glob("forecast-*.json")):
            item = _read_object(path, "forecast")
            event_id = _validated_event_id(item, path, "forecast", self.event_ids)
            if event_id in records:
                raise ValueError(f"Duplicate forecast fixture for event '{event_id}'")
            self._validate_frames(item, path)
            records[event_id] = item
        return records

    def _validate_frames(self, item: dict[str, Any], path: Path) -> None:
        frames = item.get("frames")
        if not isinstance(frames, list):
            raise ValueError(f"Invalid forecast fixture '{path.name}': frames must be an array")

        time_keys = [frame.get("timeKey") if isinstance(frame, dict) else None for frame in frames]
        if time_keys != list(self._expected_time_keys):
            expected = ", ".join(self._expected_time_keys)
            raise ValueError(
                f"Invalid forecast fixture '{path.name}': frames must be ordered {expected}"
            )

        offsets: list[int] = []
        for index, frame in enumerate(frames):
            if not isinstance(frame, dict):
                raise ValueError(f"Invalid forecast fixture '{path.name}': frame {index} must be an object")
            offset = frame.get("offsetMinutes")
            if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
                raise ValueError(
                    f"Invalid forecast fixture '{path.name}': frame {index} offsetMinutes must be a non-negative integer"
                )
            offsets.append(offset)
            for field in ("maxDepthCm", "affectedAreaKm2"):
                value = frame.get(field)
                if not _is_non_negative_number(value):
                    raise ValueError(
                        f"Invalid forecast fixture '{path.name}': frame {index} {field} must be non-negative"
                    )

        if any(current < previous for previous, current in zip(offsets, offsets[1:])):
            raise ValueError(f"Invalid forecast fixture '{path.name}': offsetMinutes must be monotonic")

    def get(self, event_id: str) -> dict[str, Any] | None:
        return self.records.get(event_id)


class AnalysisAdapter:
    """Small replaceable boundary for the current demo analysis fallback."""

    source = "DEMO_SYNTHETIC_FIXTURE"
    synthetic = True

    def __init__(self, fixture_dir: Path, event_ids: Iterable[str]) -> None:
        self.fixture_dir = fixture_dir
        self.event_ids = set(event_ids)
        self.records = self._load_records()

    def _load_records(self) -> dict[str, dict[str, Any]]:
        records: dict[str, dict[str, Any]] = {}
        for path in sorted(self.fixture_dir.glob("analysis-*.json")):
            item = _read_object(path, "analysis")
            event_id = _validated_event_id(item, path, "analysis", self.event_ids)
            if event_id in records:
                raise ValueError(f"Duplicate analysis fixture for event '{event_id}'")
            records[event_id] = item
        return records

    def get(self, event_id: str) -> dict[str, Any] | None:
        return self.records.get(event_id)


def _read_object(path: Path, kind: str) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as file:
            item = json.load(file)
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Unable to load {kind} fixture '{path.name}': {exc}") from exc
    if not isinstance(item, dict):
        raise ValueError(f"Invalid {kind} fixture '{path.name}': root must be an object")
    return item


def _validated_event_id(
    item: dict[str, Any], path: Path, kind: str, event_ids: set[str]
) -> str:
    event_id = item.get("eventId")
    if not isinstance(event_id, str) or not event_id:
        raise ValueError(f"Invalid {kind} fixture '{path.name}': eventId is required")
    if event_id not in event_ids:
        raise ValueError(
            f"Invalid {kind} fixture '{path.name}': event '{event_id}' does not exist in event fixtures"
        )
    return event_id


def _is_non_negative_number(value: Any) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(float(value))
        and value >= 0
    )
