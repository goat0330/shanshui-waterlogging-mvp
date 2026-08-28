from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from statistics import median

from ..models import SensorState


@dataclass(frozen=True)
class RiseRateEstimate:
    value_cm_min: float
    sample_count: int
    window_minutes: int
    source: str
    trend: str
    available: bool


class SensorDepthHistory:
    """Small process-local history used for realtime trend estimation.

    Persistent storage remains the responsibility of the repository layer. This
    cache is deliberately tiny and is reconstructed from incoming telemetry.
    """

    def __init__(self, max_points_per_sensor: int = 180) -> None:
        self.max_points_per_sensor = max(12, int(max_points_per_sensor))
        self._samples: dict[str, deque[SensorState]] = {}

    def add(self, state: SensorState) -> None:
        bucket = self._samples.setdefault(
            state.sensorId, deque(maxlen=self.max_points_per_sensor)
        )
        for index, existing in enumerate(bucket):
            if existing.observedAt == state.observedAt:
                bucket[index] = state
                return
        bucket.append(state)

    def estimate(
        self,
        sensor_id: str,
        *,
        now: datetime | None = None,
        window_minutes: int = 10,
    ) -> RiseRateEstimate:
        now = now or datetime.now(timezone.utc)
        bucket = self._samples.get(sensor_id)
        if not bucket:
            return RiseRateEstimate(0.0, 0, window_minutes, "NO_HISTORY", "STABLE", False)

        recent = []
        for state in bucket:
            observed = state.observedAt
            if observed.tzinfo is None:
                observed = observed.replace(tzinfo=timezone.utc)
            age_minutes = (now - observed.astimezone(timezone.utc)).total_seconds() / 60
            if -1 <= age_minutes <= window_minutes:
                recent.append(state)
        recent.sort(key=lambda item: item.observedAt)

        if len(recent) < 2:
            return RiseRateEstimate(
                0.0,
                len(recent),
                window_minutes,
                "INSUFFICIENT_HISTORY",
                "STABLE",
                False,
            )

        slopes: list[float] = []
        for left_index, left in enumerate(recent[:-1]):
            for right in recent[left_index + 1 :]:
                dt_minutes = (right.observedAt - left.observedAt).total_seconds() / 60
                if dt_minutes < 0.25:
                    continue
                slopes.append((right.depthCm - left.depthCm) / dt_minutes)

        if not slopes:
            return RiseRateEstimate(
                0.0,
                len(recent),
                window_minutes,
                "INSUFFICIENT_INTERVAL",
                "STABLE",
                False,
            )

        # Median pairwise slope: a dependency-free Theil-Sen style estimator.
        value = max(-5.0, min(5.0, float(median(slopes))))
        trend = "UP" if value > 0.1 else "DOWN" if value < -0.1 else "STABLE"
        return RiseRateEstimate(
            round(value, 3),
            len(recent),
            window_minutes,
            "ROBUST_MEDIAN_PAIRWISE_SLOPE",
            trend,
            True,
        )
