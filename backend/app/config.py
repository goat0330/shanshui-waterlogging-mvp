from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    repository_backend: str
    database_url: str | None


def load_settings() -> Settings:
    backend = os.getenv("REPOSITORY_BACKEND", "memory").strip().lower()
    if backend not in {"memory", "postgres"}:
        raise ValueError("REPOSITORY_BACKEND must be 'memory' or 'postgres'")

    database_url = os.getenv("DATABASE_URL", "").strip() or None
    if backend == "postgres" and database_url is None:
        raise ValueError("DATABASE_URL is required when REPOSITORY_BACKEND=postgres")
    return Settings(repository_backend=backend, database_url=database_url)
