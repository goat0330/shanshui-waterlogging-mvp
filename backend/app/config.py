from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    repository_backend: str
    database_url: str | None
    data_mode: str
    shanghai_water_timeout_seconds: float
    shanghai_water_cache_ttl_seconds: float
    shanghai_water_poll_interval_seconds: float = 60.0
    shanghai_water_history_points: int = 144


def load_settings() -> Settings:
    backend = os.getenv("REPOSITORY_BACKEND", "memory").strip().lower()
    if backend not in {"memory", "postgres"}:
        raise ValueError("REPOSITORY_BACKEND must be 'memory' or 'postgres'")

    database_url = os.getenv("DATABASE_URL", "").strip() or None
    if backend == "postgres" and database_url is None:
        raise ValueError("DATABASE_URL is required when REPOSITORY_BACKEND=postgres")

    data_mode = os.getenv("DATA_MODE", "fixture").strip().lower()
    if data_mode not in {"fixture", "hybrid", "real"}:
        raise ValueError("DATA_MODE must be 'fixture', 'hybrid' or 'real'")

    timeout_seconds = _positive_float("SHANGHAI_WATER_TIMEOUT_SECONDS", 8.0)
    cache_ttl_seconds = _positive_float("SHANGHAI_WATER_CACHE_TTL_SECONDS", 45.0)
    poll_interval_seconds = _positive_float("SHANGHAI_WATER_POLL_INTERVAL_SECONDS", 60.0)
    history_points = _positive_int("SHANGHAI_WATER_HISTORY_POINTS", 144)
    return Settings(
        repository_backend=backend,
        database_url=database_url,
        data_mode=data_mode,
        shanghai_water_timeout_seconds=timeout_seconds,
        shanghai_water_cache_ttl_seconds=cache_ttl_seconds,
        shanghai_water_poll_interval_seconds=poll_interval_seconds,
        shanghai_water_history_points=history_points,
    )


def _positive_float(name: str, default: float) -> float:
    raw = os.getenv(name, str(default)).strip()
    try:
        value = float(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be a positive number") from exc
    if value <= 0:
        raise ValueError(f"{name} must be a positive number")
    return value


def _positive_int(name: str, default: int) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be a positive integer") from exc
    if value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value
