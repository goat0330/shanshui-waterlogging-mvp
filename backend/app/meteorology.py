from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .models import (
    MeteorologyContext,
    MeteorologyDataStatus,
    MeteorologyMode,
    MeteorologyNowcast,
    MeteorologyNowcastFrame,
    MeteorologyRainfallNow,
    MeteorologyRainfallStation,
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
    """Compose the provisional meteorology context without changing flood state."""

    WARNING_SOURCE = "NATIONAL_WEATHER_WARNING"
    NOWCAST_SOURCE = "CMA_RADAR_NOWCAST"

    def __init__(self, shanghai_water_adapter: ShanghaiWaterAdapter) -> None:
        self.shanghai_water_adapter = shanghai_water_adapter

    def get(self, data_mode: str) -> MeteorologyContext:
        received_at = datetime.now(timezone.utc)
        if data_mode == MeteorologyMode.FIXTURE.value:
            return self._fixture_context(received_at)

        try:
            # Context only needs rainfallNow; other water datasets remain visible in
            # sourceHealth but must not prevent a degraded real context.
            snapshot = self.shanghai_water_adapter.fetch(allow_partial=True)
        except ShanghaiWaterError as exc:
            if data_mode == MeteorologyMode.REAL.value:
                raise MeteorologyError("METEOROLOGY_UNAVAILABLE", exc.message) from exc
            return self._degraded_context(data_mode, received_at, exc.code)

        if not snapshot.rainfall:
            if data_mode == MeteorologyMode.REAL.value:
                raise MeteorologyError(
                    "METEOROLOGY_RAINFALL_UNAVAILABLE",
                    "Shanghai Water Bureau returned no rainfall stations",
                )
            return self._degraded_context(data_mode, received_at, "SHANGHAI_WATER_RAINFALL_EMPTY")

        rainfall = [self._rainfall_station(item, snapshot.coordinateReference) for item in snapshot.rainfall]
        source_health = self._source_health(snapshot, received_at)
        source_health.extend(self._unverified_health(received_at))
        observed_at = max(item.observedAt for item in rainfall)
        status = (
            MeteorologyDataStatus.DEGRADED
            if data_mode == MeteorologyMode.REAL.value
            else MeteorologyDataStatus.MIXED
        )
        return MeteorologyContext(
            observedAt=observed_at,
            receivedAt=received_at,
            source=ShanghaiWaterAdapter.SOURCE,
            coordinateReference=snapshot.coordinateReference,
            mode=MeteorologyMode(data_mode),
            dataStatus=status,
            warnings=[],
            rainfallNow=MeteorologyRainfallNow(stations=rainfall),
            nowcast=MeteorologyNowcast(frames=[]),
            sourceHealth=source_health,
        )

    def _fixture_context(self, received_at: datetime) -> MeteorologyContext:
        return MeteorologyContext(
            receivedAt=received_at,
            source="FIXTURE_SYNTHETIC",
            mode=MeteorologyMode.FIXTURE,
            dataStatus=MeteorologyDataStatus.SYNTHETIC,
            warnings=[],
            rainfallNow=MeteorologyRainfallNow(stations=[]),
            nowcast=MeteorologyNowcast(frames=self._synthetic_frames(received_at)),
            sourceHealth=[
                MeteorologySourceHealth(
                    provider="FIXTURE",
                    sourceId="RAINFALL_NOW",
                    status=MeteorologySourceHealthStatus.SYNTHETIC,
                    receivedAt=received_at,
                    message="No synthetic rainfall stations are invented in the fixture context",
                ),
                *self._unverified_health(received_at),
            ],
        )

    def _degraded_context(
        self,
        data_mode: str,
        received_at: datetime,
        error_code: str,
    ) -> MeteorologyContext:
        return MeteorologyContext(
            receivedAt=received_at,
            source="METEOROLOGY_DEGRADED",
            mode=MeteorologyMode(data_mode),
            dataStatus=MeteorologyDataStatus.DEGRADED,
            warnings=[],
            rainfallNow=MeteorologyRainfallNow(stations=[]),
            nowcast=MeteorologyNowcast(frames=[]),
            sourceHealth=[
                MeteorologySourceHealth(
                    provider=ShanghaiWaterAdapter.SOURCE,
                    sourceId="RAINFALL_NOW",
                    status=MeteorologySourceHealthStatus.UNAVAILABLE,
                    receivedAt=received_at,
                    message=error_code,
                ),
                *self._unverified_health(received_at),
            ],
        )

    @staticmethod
    def _rainfall_station(item: object, coordinate_reference: str) -> MeteorologyRainfallStation:
        return MeteorologyRainfallStation(
            stationId=item.stationId,
            stationName=item.stationName,
            district=item.district,
            coordinates=item.coordinates,
            coordinateReference=coordinate_reference,
            rainfallValue=item.rainfallValue,
            unit="mm",
            windowMinutes=None,
            observedAt=item.observedAt,
            sourceId=item.sourceId,
            synthetic=False,
        )

    @staticmethod
    def _source_health(
        snapshot: ShanghaiWaterSnapshot,
        received_at: datetime,
    ) -> list[MeteorologySourceHealth]:
        status_map = {
            ShanghaiWaterSourceStatus.OK: MeteorologySourceHealthStatus.OK,
            ShanghaiWaterSourceStatus.SCHEMA_MISMATCH: MeteorologySourceHealthStatus.SCHEMA_MISMATCH,
            ShanghaiWaterSourceStatus.UNAVAILABLE: MeteorologySourceHealthStatus.UNAVAILABLE,
            ShanghaiWaterSourceStatus.EMPTY: MeteorologySourceHealthStatus.UNAVAILABLE,
        }
        return [
            MeteorologySourceHealth(
                provider=ShanghaiWaterAdapter.SOURCE,
                sourceId=dataset_type,
                status=status_map[health.status],
                observedAt=health.observedLatestAt,
                receivedAt=health.fetchedAt or received_at,
                message=health.errorCode,
            )
            for dataset_type, health in sorted(snapshot.sourceHealth.items())
        ]

    @classmethod
    def _unverified_health(cls, received_at: datetime) -> list[MeteorologySourceHealth]:
        return [
            MeteorologySourceHealth(
                provider=cls.WARNING_SOURCE,
                sourceId="WARNING_API_UNVERIFIED",
                status=MeteorologySourceHealthStatus.NOT_VERIFIED,
                receivedAt=received_at,
                message="No stable anonymous machine-readable warning API verified",
            ),
            MeteorologySourceHealth(
                provider=cls.NOWCAST_SOURCE,
                sourceId="RADAR_NOWCAST_UNVERIFIED",
                status=MeteorologySourceHealthStatus.NOT_VERIFIED,
                receivedAt=received_at,
                message="No authorized georeferenced radar/nowcast source verified",
            ),
        ]

    @staticmethod
    def _synthetic_frames(received_at: datetime) -> list[MeteorologyNowcastFrame]:
        return [
            MeteorologyNowcastFrame(
                offsetMinutes=offset,
                validAt=received_at + timedelta(minutes=offset),
                sourceId="FIXTURE_NOWCAST_UNAVAILABLE",
                georeferenced=False,
                renderableInCesium=False,
                synthetic=True,
            )
            for offset in (0, 30, 60, 120)
        ]
