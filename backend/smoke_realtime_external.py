from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from app.models import ShanghaiWaterSnapshot
from app.realtime_external import ShanghaiWaterRealtimeCollector
from app.shanghai_water import ShanghaiWaterError


class FakeAdapter:
    def __init__(self) -> None:
        self.calls = 0

    def fetch(self, *, allow_partial: bool = True) -> ShanghaiWaterSnapshot:
        self.calls += 1
        if self.calls == 3:
            raise ShanghaiWaterError("TEST_FAILURE", "simulated upstream failure")
        observed = datetime(2026, 8, 27, 0, 0, tzinfo=timezone.utc) + timedelta(minutes=10 * (self.calls - 1))
        value = float(self.calls - 1)
        now = datetime.now(timezone.utc)
        return ShanghaiWaterSnapshot.model_validate({
            "source": "TEST_SHANGHAI_WATER",
            "fetchedAt": now,
            "receivedAt": now,
            "sourceStatus": "ok",
            "sourceHealth": {},
            "coordinateReference": "SOURCE_REPORTED_XX2000_YY2000",
            "sourceUrls": ["https://example.invalid/test"],
            "rainfall": [{
                "stationId": "R-001",
                "sourceId": "R-001",
                "stationName": "测试站",
                "coordinates": {"lat": 31.2, "lon": 121.4},
                "rainfallValue": value,
                "observedAt": observed,
                "receivedAt": now,
                "provider": "TEST",
                "synthetic": False,
                "rawSource": "https://example.invalid/test",
            }],
            "ponding": [],
            "waterLevels": [],
            "waterLevelForecast": [],
        })


async def main() -> None:
    broadcasts: list[tuple[str, dict]] = []

    async def broadcast(kind: str, payload: dict) -> None:
        broadcasts.append((kind, payload))

    collector = ShanghaiWaterRealtimeCollector(
        FakeAdapter(),  # type: ignore[arg-type]
        data_mode="hybrid",
        poll_interval_seconds=60,
        history_points_per_station=8,
    )
    collector._broadcast = broadcast  # smoke only; avoids starting a background task.

    first = await collector.refresh_now()
    assert first.status.value == "ready"
    assert first.snapshot is not None
    assert len(first.rainfallHistory["R-001"]) == 1
    assert first.sourceChangedThisPoll is True
    assert first.rainfallChangedThisPoll is True

    second = await collector.refresh_now()
    assert second.snapshot is not None
    assert second.snapshot.rainfall[0].rainfallValue == 1.0
    assert len(second.rainfallHistory["R-001"]) == 2
    assert second.sourceChangedThisPoll is True
    last_good = second.snapshot.fetchedAt

    failed = await collector.refresh_now()
    assert failed.status.value == "degraded"
    assert failed.snapshot is not None
    assert failed.snapshot.fetchedAt == last_good
    assert failed.consecutiveFailures == 1
    assert failed.lastError and "TEST_FAILURE" in failed.lastError
    assert len(broadcasts) == 3
    assert all(kind == "external.shanghai_water.updated" for kind, _ in broadcasts)

    fixture = ShanghaiWaterRealtimeCollector(FakeAdapter(), data_mode="fixture")  # type: ignore[arg-type]
    assert fixture.state().status.value == "disabled"
    print("realtime external smoke: PASS")


if __name__ == "__main__":
    asyncio.run(main())
