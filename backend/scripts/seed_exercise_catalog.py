"""Seed the exercise catalog from the bundled snapshot into the database.

Usage:
    python scripts/seed_exercise_catalog.py                 # bundled asset
    python scripts/seed_exercise_catalog.py catalog.json    # custom snapshot
Run from the ``backend/`` directory (or with ``backend/app`` on PYTHONPATH).
"""

import os
import sys
from pathlib import Path

_APP_DIR = Path(__file__).resolve().parent.parent / "app"
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))

os.environ.setdefault("DB_PASSWORD", "seed-placeholder")
os.environ.setdefault("SECRET_KEY", "seed-placeholder")

from sqlalchemy.orm import Session  # noqa: E402

import workouts.exercise_catalog as exercise_catalog  # noqa: E402
from core.database import engine  # noqa: E402


def main() -> int:
    custom = sys.argv[1] if len(sys.argv) > 1 else None
    with Session(engine) as db:
        count = exercise_catalog.seed_catalog(db, custom)
    print(f"Seeded {count} exercises into exercise_catalog")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
