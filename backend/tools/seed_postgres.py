from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import create_engine

from app.config import load_settings
from app.db.seed import seed_database


def main() -> None:
    parser = argparse.ArgumentParser(description="Idempotently seed the V1 PostgreSQL/PostGIS fixtures")
    parser.add_argument("--database-url", default=None)
    parser.add_argument(
        "--fixture-dir",
        type=Path,
        default=BACKEND_DIR.parent / "contracts" / "fixtures",
    )
    args = parser.parse_args()

    settings = load_settings()
    database_url = args.database_url or settings.database_url
    if not database_url:
        raise SystemExit("DATABASE_URL or --database-url is required")

    engine = create_engine(database_url, pool_pre_ping=True)
    try:
        counts = seed_database(engine, args.fixture_dir)
    finally:
        engine.dispose()
    print("seed: PASS " + ", ".join(f"{key}={value}" for key, value in counts.items()))


if __name__ == "__main__":
    main()
