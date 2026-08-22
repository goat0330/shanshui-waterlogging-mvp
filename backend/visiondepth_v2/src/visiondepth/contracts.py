from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class VisionDepthFrameEvidence:
    """Timestamp wrapper; the nested observation keeps the existing contract."""

    frame_id: str
    timestamp_ms: int
    observation: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "frameId": self.frame_id,
            "timestampMs": self.timestamp_ms,
            "observation": self.observation,
        }

