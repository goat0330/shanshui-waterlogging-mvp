from __future__ import annotations

from app.cma_source import CmaSourceAdapter
from app.models import MeteorologySourceHealthStatus


def main() -> int:
    result = CmaSourceAdapter.from_env().fetch()
    print("meteorology live source health")
    for health in result.source_health:
        print(
            f"- {health.provider}: {health.status.value}"
            f" | observed={health.observedAt or '-'}"
            f" | {health.message or health.sourceId}"
        )
    print(f"current={'yes' if result.current else 'no'}")
    print(f"warnings={len(result.warnings)}")
    print(f"radar_frames={len(result.radar_frames)}")
    print(f"nowcast_frames={len(result.frames)}")

    required = {
        "NMC_CURRENT_WEATHER",
        "NMC_WEATHER_WARNING",
        "CHINA_WEATHER_MINUTE_NOWCAST",
    }
    bad = [
        health for health in result.source_health
        if health.provider in required and health.status != MeteorologySourceHealthStatus.OK
    ]
    if bad:
        print("LIVE SOURCE SMOKE: DEGRADED")
        return 2
    print("LIVE SOURCE SMOKE: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
