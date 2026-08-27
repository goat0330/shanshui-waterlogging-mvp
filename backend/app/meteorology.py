from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .cma_source import CmaContextResult, CmaSourceAdapter
from .models import (
    MeteorologyContext,
    MeteorologyDataStatus,
    MeteorologyMode,
    MeteorologyNowcast,
    MeteorologyNowcastFrame,
    MeteorologyRainfallNow,
    MeteorologyRainfallStation,
    MeteorologyRadar,
    MeteorologySourceHealth,
    MeteorologySourceHealthStatus,
    ShanghaiWaterSnapshot,
    ShanghaiWaterSourceStatus,
)
from .shanghai_water import ShanghaiWaterAdapter, ShanghaiWaterError


class MeteorologyError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class MeteorologyContextService:
    """Compose rainfall + warning + radar/nowcast metadata without mutating flood state."""

    def __init__(self, shanghai_water_adapter: ShanghaiWaterAdapter, cma_adapter: CmaSourceAdapter | None = None) -> None:
        self.shanghai_water_adapter = shanghai_water_adapter
        self.cma_adapter = cma_adapter or CmaSourceAdapter.from_env()

    def get(self, data_mode: str) -> MeteorologyContext:
        received_at = datetime.now(timezone.utc)
        if data_mode == MeteorologyMode.FIXTURE.value:
            return self._fixture_context(received_at)

        cma = self.cma_adapter.fetch(received_at)
        try:
            snapshot = self.shanghai_water_adapter.fetch(allow_partial=True)
        except ShanghaiWaterError as exc:
            return self._degraded_context(data_mode, received_at, exc.code, cma)

        if not snapshot.rainfall:
            return self._degraded_context(data_mode, received_at, "SHANGHAI_WATER_RAINFALL_EMPTY", cma)

        rainfall = [self._rainfall_station(item, snapshot.coordinateReference) for item in snapshot.rainfall]
        source_health = self._source_health(snapshot, received_at) + cma.source_health
        observed_candidates = [max(item.observedAt for item in rainfall)]
        if cma.observed_at is not None:
            observed_candidates.append(cma.observed_at)

        cma_ok = all(item.status == MeteorologySourceHealthStatus.OK for item in cma.source_health)
        if data_mode == MeteorologyMode.REAL.value:
            status = MeteorologyDataStatus.REAL if cma_ok else MeteorologyDataStatus.DEGRADED
        else:
            status = MeteorologyDataStatus.MIXED

        return MeteorologyContext(
            observedAt=max(observed_candidates),
            receivedAt=received_at,
            source="SHANGHAI_WATER+NMC+CHINA_WEATHER" if cma_ok else "SHANGHAI_WATER+METEOROLOGY_PARTIAL",
            coordinateReference=snapshot.coordinateReference,
            mode=MeteorologyMode(data_mode),
            dataStatus=status,
            current=cma.current,
            warnings=cma.warnings,
            rainfallNow=MeteorologyRainfallNow(stations=rainfall),
            radar=MeteorologyRadar(frames=cma.radar_frames),
            nowcast=MeteorologyNowcast(frames=cma.frames),
            sourceHealth=source_health,
        )

    def _fixture_context(self, received_at: datetime) -> MeteorologyContext:
        # Fixture mode must stay network-free even when local CMA URLs are configured.
        cma = CmaSourceAdapter().fetch(received_at)
        return MeteorologyContext(
            receivedAt=received_at,
            source="FIXTURE_SYNTHETIC",
            mode=MeteorologyMode.FIXTURE,
            dataStatus=MeteorologyDataStatus.SYNTHETIC,
            current=None,
            warnings=[],
            rainfallNow=MeteorologyRainfallNow(stations=[]),
            radar=MeteorologyRadar(),
            nowcast=MeteorologyNowcast(frames=self._synthetic_frames(received_at)),
            sourceHealth=[
                MeteorologySourceHealth(
                    provider="FIXTURE", sourceId="RAINFALL_NOW",
                    status=MeteorologySourceHealthStatus.SYNTHETIC,
                    receivedAt=received_at,
                    message="No synthetic rainfall stations are invented in the fixture context",
                ),
                *cma.source_health,
            ],
        )

    def _degraded_context(self, data_mode: str, received_at: datetime, error_code: str, cma: CmaContextResult) -> MeteorologyContext:
        return MeteorologyContext(
            observedAt=cma.observed_at,
            receivedAt=received_at,
            source="METEOROLOGY_DEGRADED",
            mode=MeteorologyMode(data_mode),
            dataStatus=MeteorologyDataStatus.DEGRADED,
            current=cma.current,
            warnings=cma.warnings,
            rainfallNow=MeteorologyRainfallNow(stations=[]),
            radar=MeteorologyRadar(frames=cma.radar_frames),
            nowcast=MeteorologyNowcast(frames=cma.frames),
            sourceHealth=[
                MeteorologySourceHealth(
                    provider=ShanghaiWaterAdapter.SOURCE, sourceId="RAINFALL_NOW",
                    status=MeteorologySourceHealthStatus.UNAVAILABLE,
                    receivedAt=received_at, message=error_code,
                ),
                *cma.source_health,
            ],
        )

    @staticmethod
    def _rainfall_station(item: object, coordinate_reference: str) -> MeteorologyRainfallStation:
        return MeteorologyRainfallStation(
            stationId=item.stationId, stationName=item.stationName,
            district=item.district, coordinates=item.coordinates,
            coordinateReference=coordinate_reference, rainfallValue=item.rainfallValue,
            unit="mm", windowMinutes=None, observedAt=item.observedAt,
            sourceId=item.sourceId, synthetic=False,
        )

    @staticmethod
    def _source_health(snapshot: ShanghaiWaterSnapshot, received_at: datetime) -> list[MeteorologySourceHealth]:
        status_map = {
            ShanghaiWaterSourceStatus.OK: MeteorologySourceHealthStatus.OK,
            ShanghaiWaterSourceStatus.SCHEMA_MISMATCH: MeteorologySourceHealthStatus.SCHEMA_MISMATCH,
            ShanghaiWaterSourceStatus.UNAVAILABLE: MeteorologySourceHealthStatus.UNAVAILABLE,
            ShanghaiWaterSourceStatus.EMPTY: MeteorologySourceHealthStatus.UNAVAILABLE,
        }
        return [
            MeteorologySourceHealth(
                provider=ShanghaiWaterAdapter.SOURCE, sourceId=dataset_type,
                status=status_map[health.status], observedAt=health.observedLatestAt,
                receivedAt=health.fetchedAt or received_at,
                message=health.errorCode or health.fallbackReason,
            )
            for dataset_type, health in sorted(snapshot.sourceHealth.items())
        ]

    @staticmethod
    def _synthetic_frames(received_at: datetime) -> list[MeteorologyNowcastFrame]:
        return [
            MeteorologyNowcastFrame(
                offsetMinutes=offset, validAt=received_at + timedelta(minutes=offset),
                sourceId="FIXTURE_NOWCAST_UNAVAILABLE", georeferenced=False,
                renderableInCesium=False, synthetic=True,
            )
            for offset in (0, 30, 60, 120)
        ]
