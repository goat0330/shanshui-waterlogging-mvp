from __future__ import annotations

import asyncio
import time
from collections import deque
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable

from .models import (
    ShanghaiWaterRainfallHistoryPoint,
    ShanghaiWaterRealtimeState,
    ShanghaiWaterRealtimeStatus,
    ShanghaiWaterSnapshot,
)
from .shanghai_water import ShanghaiWaterAdapter, ShanghaiWaterError

BroadcastCallback = Callable[[str, dict[str, Any]], Awaitable[None]]


class ShanghaiWaterRealtimeCollector:
    """Backend-owned Shanghai Water polling, history, freshness and WS projection.

    The public-source adapter remains responsible for upstream normalization.
    This collector only owns runtime state: polling cadence, last-good snapshot,
    observation history and realtime notifications.
    """

    def __init__(
        self,
        adapter: ShanghaiWaterAdapter,
        *,
        data_mode: str,
        poll_interval_seconds: float = 60.0,
        history_points_per_station: int = 144,
    ) -> None:
        if data_mode not in {"fixture", "hybrid", "real"}:
            raise ValueError("data_mode must be fixture, hybrid or real")
        if poll_interval_seconds <= 0:
            raise ValueError("poll_interval_seconds must be positive")
        if history_points_per_station <= 0:
            raise ValueError("history_points_per_station must be positive")

        self.adapter = adapter
        self.data_mode = data_mode
        self.poll_interval_seconds = poll_interval_seconds
        self.history_points_per_station = history_points_per_station
        self._snapshot: ShanghaiWaterSnapshot | None = None
        self._history: dict[str, deque[ShanghaiWaterRainfallHistoryPoint]] = {}
        self._status = (
            ShanghaiWaterRealtimeStatus.DISABLED
            if data_mode == "fixture"
            else ShanghaiWaterRealtimeStatus.LOADING
        )
        self._polled_at: datetime | None = None
        self._last_successful_poll_at: datetime | None = None
        self._source_changed_at: datetime | None = None
        self._latest_source_observed_at: datetime | None = None
        self._source_changed_this_poll = False
        self._rainfall_changed_this_poll = False
        self._last_error: str | None = None
        self._consecutive_failures = 0
        self._last_signature: tuple[Any, ...] | None = None
        self._last_rainfall_signature: tuple[Any, ...] | None = None
        self._broadcast: BroadcastCallback | None = None
        self._task: asyncio.Task[None] | None = None
        self._stop_event = asyncio.Event()
        self._refresh_lock = asyncio.Lock()

    def state(self) -> ShanghaiWaterRealtimeState:
        return ShanghaiWaterRealtimeState(
            status=self._status,
            pollIntervalSeconds=self.poll_interval_seconds,
            polledAt=self._polled_at,
            lastSuccessfulPollAt=self._last_successful_poll_at,
            sourceChangedAt=self._source_changed_at,
            sourceChangedThisPoll=self._source_changed_this_poll,
            rainfallChangedThisPoll=self._rainfall_changed_this_poll,
            latestSourceObservedAt=self._latest_source_observed_at,
            consecutiveFailures=self._consecutive_failures,
            lastError=self._last_error,
            snapshot=self._snapshot,
            rainfallHistory={station_id: list(points) for station_id, points in self._history.items()},
        )

    async def start(self, broadcast: BroadcastCallback | None = None) -> None:
        self._broadcast = broadcast
        if self.data_mode == "fixture":
            self._status = ShanghaiWaterRealtimeStatus.DISABLED
            return
        if self._task is not None and not self._task.done():
            return
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run(), name="shanghai-water-realtime-collector")

    async def stop(self) -> None:
        self._stop_event.set()
        task = self._task
        self._task = None
        if task is None:
            return
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    async def refresh_now(self) -> ShanghaiWaterRealtimeState:
        if self.data_mode == "fixture":
            return self.state()

        async with self._refresh_lock:
            self._status = ShanghaiWaterRealtimeStatus.LOADING if self._snapshot is None else self._status
            self._source_changed_this_poll = False
            self._rainfall_changed_this_poll = False
            self._polled_at = datetime.now(timezone.utc)
            try:
                snapshot = await asyncio.to_thread(
                    self.adapter.fetch,
                    allow_partial=self.data_mode == "hybrid",
                )
            except ShanghaiWaterError as exc:
                self._consecutive_failures += 1
                self._last_error = f"{exc.code}: {exc.message}"
                self._status = ShanghaiWaterRealtimeStatus.DEGRADED
            except Exception as exc:  # Runtime boundary: keep last-good data available.
                self._consecutive_failures += 1
                self._last_error = f"SHANGHAI_WATER_COLLECTOR_FAILED: {exc}"
                self._status = ShanghaiWaterRealtimeStatus.DEGRADED
            else:
                self._ingest(snapshot)
                self._snapshot = snapshot
                self._last_successful_poll_at = self._polled_at
                self._consecutive_failures = 0
                self._last_error = None
                self._status = (
                    ShanghaiWaterRealtimeStatus.READY
                    if snapshot.sourceStatus == "ok"
                    else ShanghaiWaterRealtimeStatus.DEGRADED
                )

            state = self.state()

        if self._broadcast is not None:
            await self._broadcast(
                "external.shanghai_water.updated",
                state.model_dump(mode="json", exclude_none=True),
            )
        return state

    async def _run(self) -> None:
        while not self._stop_event.is_set():
            started = time.monotonic()
            await self.refresh_now()
            remaining = max(0.5, self.poll_interval_seconds - (time.monotonic() - started))
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=remaining)
            except asyncio.TimeoutError:
                continue

    def _ingest(self, snapshot: ShanghaiWaterSnapshot) -> None:
        signature = self._snapshot_signature(snapshot)
        rainfall_signature = tuple(sorted((item.stationId, item.observedAt.isoformat(), item.rainfallValue) for item in snapshot.rainfall))
        if signature != self._last_signature:
            self._source_changed_this_poll = True
            self._source_changed_at = self._polled_at
            self._last_signature = signature
        if rainfall_signature != self._last_rainfall_signature:
            self._rainfall_changed_this_poll = True
            self._last_rainfall_signature = rainfall_signature

        observation_times: list[datetime] = []
        for station in snapshot.rainfall:
            observation_times.append(station.observedAt)
            history = self._history.setdefault(
                station.stationId,
                deque(maxlen=self.history_points_per_station),
            )
            point = ShanghaiWaterRainfallHistoryPoint(
                stationId=station.stationId,
                stationName=station.stationName,
                observedAt=station.observedAt,
                rainfallValue=station.rainfallValue,
            )
            if history and history[-1].observedAt == point.observedAt and history[-1].rainfallValue == point.rainfallValue:
                continue
            history.append(point)

        observation_times.extend(item.observedAt for item in snapshot.ponding)
        observation_times.extend(item.observedAt for item in snapshot.waterLevels)
        self._latest_source_observed_at = max(observation_times) if observation_times else None

    @staticmethod
    def _snapshot_signature(snapshot: ShanghaiWaterSnapshot) -> tuple[Any, ...]:
        rainfall = tuple(
            sorted((item.stationId, item.observedAt.isoformat(), item.rainfallValue) for item in snapshot.rainfall)
        )
        ponding = tuple(
            sorted((item.siteId, item.observedAt.isoformat(), item.depthCm) for item in snapshot.ponding)
        )
        water_levels = tuple(
            sorted((item.stationId, item.observedAt.isoformat(), item.outWaterM) for item in snapshot.waterLevels)
        )
        forecasts = tuple(
            sorted((item.stationId, item.forecastAt.isoformat(), item.forecastWaterLevelM) for item in snapshot.waterLevelForecast)
        )
        return rainfall, ponding, water_levels, forecasts
