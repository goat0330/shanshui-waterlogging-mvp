from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable

from .meteorology import MeteorologyContextService, MeteorologyError
from .models import (
    MeteorologyContext,
    MeteorologyDataStatus,
    MeteorologyRealtimeState,
    MeteorologyRealtimeStatus,
    MeteorologySourceHealthStatus,
)

BroadcastCallback = Callable[[str, dict[str, Any]], Awaitable[None]]


class MeteorologyRealtimeCollector:
    """Backend-owned meteorology polling with last-good state and WS projection."""

    def __init__(
        self,
        service: MeteorologyContextService,
        *,
        data_mode: str,
        poll_interval_seconds: float = 360.0,
    ) -> None:
        if data_mode not in {"fixture", "hybrid", "real"}:
            raise ValueError("data_mode must be fixture, hybrid or real")
        if poll_interval_seconds <= 0:
            raise ValueError("poll_interval_seconds must be positive")
        self.service = service
        self.data_mode = data_mode
        self.poll_interval_seconds = poll_interval_seconds
        self._context: MeteorologyContext | None = None
        self._status = (
            MeteorologyRealtimeStatus.DISABLED
            if data_mode == "fixture"
            else MeteorologyRealtimeStatus.LOADING
        )
        self._polled_at: datetime | None = None
        self._last_successful_poll_at: datetime | None = None
        self._source_changed_at: datetime | None = None
        self._source_changed_this_poll = False
        self._latest_source_observed_at: datetime | None = None
        self._consecutive_failures = 0
        self._last_error: str | None = None
        self._last_signature: tuple[Any, ...] | None = None
        self._broadcast: BroadcastCallback | None = None
        self._task: asyncio.Task[None] | None = None
        self._stop_event = asyncio.Event()
        self._refresh_lock = asyncio.Lock()

    def state(self) -> MeteorologyRealtimeState:
        return MeteorologyRealtimeState(
            status=self._status,
            pollIntervalSeconds=self.poll_interval_seconds,
            polledAt=self._polled_at,
            lastSuccessfulPollAt=self._last_successful_poll_at,
            sourceChangedAt=self._source_changed_at,
            sourceChangedThisPoll=self._source_changed_this_poll,
            latestSourceObservedAt=self._latest_source_observed_at,
            consecutiveFailures=self._consecutive_failures,
            lastError=self._last_error,
            context=self._context,
        )

    async def start(self, broadcast: BroadcastCallback | None = None) -> None:
        self._broadcast = broadcast
        if self.data_mode == "fixture":
            self._status = MeteorologyRealtimeStatus.DISABLED
            return
        if self._task is not None and not self._task.done():
            return
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run(), name="meteorology-realtime-collector")

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

    async def refresh_now(self) -> MeteorologyRealtimeState:
        if self.data_mode == "fixture":
            return self.state()

        async with self._refresh_lock:
            self._source_changed_this_poll = False
            self._polled_at = datetime.now(timezone.utc)
            try:
                context = await asyncio.to_thread(self.service.get, self.data_mode)
            except MeteorologyError as exc:
                self._record_failure(f"{exc.code}: {exc.message}")
            except Exception as exc:  # runtime boundary
                self._record_failure(f"METEOROLOGY_COLLECTOR_FAILED: {exc}")
            else:
                usable = self._has_real_meteorology(context)
                if usable or self._context is None:
                    signature = self._signature(context)
                    if signature != self._last_signature:
                        self._source_changed_this_poll = True
                        self._source_changed_at = self._polled_at
                        self._last_signature = signature
                    self._context = context
                    self._latest_source_observed_at = context.observedAt
                self._last_successful_poll_at = self._polled_at
                self._consecutive_failures = 0
                self._last_error = None if usable else "No real meteorology payload; retaining last-good context when available"
                provider_health = [
                    item for item in context.sourceHealth
                    if item.provider.startswith(("NMC_", "CHINA_WEATHER", "CMA_"))
                ]
                providers_ok = bool(provider_health) and all(
                    item.status == MeteorologySourceHealthStatus.OK for item in provider_health
                )
                self._status = (
                    MeteorologyRealtimeStatus.READY
                    if usable and providers_ok and context.dataStatus != MeteorologyDataStatus.DEGRADED
                    else MeteorologyRealtimeStatus.DEGRADED
                )

            state = self.state()

        if self._broadcast is not None:
            await self._broadcast(
                "meteorology.updated",
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

    def _record_failure(self, message: str) -> None:
        self._consecutive_failures += 1
        self._last_error = message
        self._status = MeteorologyRealtimeStatus.DEGRADED

    @staticmethod
    def _has_real_meteorology(context: MeteorologyContext) -> bool:
        if context.current is not None and not context.current.synthetic:
            return True
        if any(not item.synthetic for item in context.warnings):
            return True
        if any(not item.synthetic for item in context.radar.frames):
            return True
        if any(not item.synthetic for item in context.nowcast.frames):
            return True
        return False

    @staticmethod
    def _signature(context: MeteorologyContext) -> tuple[Any, ...]:
        current = None
        if context.current is not None:
            current = (
                context.current.stationId,
                context.current.observedAt.isoformat(),
                context.current.temperatureC,
                context.current.condition,
                context.current.rainfallMm,
            )
        warnings = tuple(sorted(
            (item.sourceId, item.issuedAt.isoformat(), item.type, item.level)
            for item in context.warnings
        ))
        radar = tuple(sorted(
            (item.sourceId, item.previewUrl, item.observedAt.isoformat())
            for item in context.radar.frames
        ))
        nowcast = tuple(
            (item.offsetMinutes, item.summary, item.precipitationValue)
            for item in context.nowcast.frames
            if not item.synthetic
        )
        return current, warnings, radar, nowcast
