"""Exercise catalog backed by the wger project's CC-BY-SA exercise data.

The catalog is baked into ZAPFIT: a snapshot (`backend/assets/exercise_catalog.json`,
generated from wger's Django fixtures) is seeded into the database by
`scripts/seed_exercise_catalog.py` (also invoked automatically on container
start when the table is empty). It powers the strength-workout UI — exercise
picker, search, muscle/equipment filters — fully offline, without any wger
integration or API key. Only plan import from a user's own wger instance uses
the optional integration.

Data model note: `wger_id` is the stable wger exercise-base id used by plans
and set logs (`workout_plan_exercises.wger_exercise_id`,
`workout_sets.wger_exercise_id`) so joins stay meaningful across re-seeds.
Translation quality varies per language; the UI falls back to the English
name (always present) when a language is missing.
"""

import json as json_module
from datetime import datetime as datetime_type
from functools import lru_cache
from pathlib import Path
from typing import Any

from sqlalchemy import JSON, DateTime, Integer, String, func, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from core.database import Base

# Layouts seen in the wild (first existing wins):
# - repo/dev checkout:  backend/app/workouts/* -> parents[2] = backend
# - Docker image:       /app/backend/workouts/* -> parents[2] = /app
# Older published images packaged the snapshot at /app/backend/assets
# (COPY backend/assets ./assets under WORKDIR /app/backend) — check it too so
# the loader works regardless of which Dockerfile produced the image.
_CATALOG_FILENAME = "exercise_catalog.json"
_CATALOG_SEARCH = (
    Path(__file__).resolve().parents[2] / "assets" / _CATALOG_FILENAME,
    Path(__file__).resolve().parents[1] / "assets" / _CATALOG_FILENAME,
    Path("/app") / "assets" / _CATALOG_FILENAME,
)
_CATALOG_ASSET = _CATALOG_SEARCH[0]


class ExerciseCatalog(Base):
    __tablename__ = "exercise_catalog"

    wger_id: Mapped[int] = mapped_column(primary_key=True)
    uuid: Mapped[str] = mapped_column(String(50), nullable=False, unique=True, index=True)
    # Canonical English name (search column); per-language names/descriptions
    # live in the translations JSON mapping language -> {name, description}.
    name: Mapped[str] = mapped_column(String(250), nullable=False, index=True)
    translations: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    category_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    equipment_ids: Mapped[list[int]] = mapped_column(JSON, nullable=False, server_default="[]")
    muscle_ids: Mapped[list[int]] = mapped_column(JSON, nullable=False, server_default="[]")
    muscle_ids_secondary: Mapped[list[int]] = mapped_column(JSON, nullable=False, server_default="[]")
    variation_group: Mapped[str | None] = mapped_column(String(50), nullable=True)
    license_author: Mapped[str | None] = mapped_column(String(250), nullable=True)
    # Enrichment harvested from wger's fixtures (see scripts/generate_exercise_catalog.py):
    # alternative exercise names per language (search synonyms) and short
    # technique tips per language, both keyed by language code.
    aliases: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, server_default="{}")
    tips: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, server_default="{}")
    license_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    updated_at: Mapped[datetime_type] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


@lru_cache(maxsize=1)
def load_snapshot() -> dict:
    """Load the bundled catalog snapshot (categories, equipment, muscles, exercises)."""
    asset = next((path for path in _CATALOG_SEARCH if path.is_file()), _CATALOG_SEARCH[0])
    try:
        with open(asset, encoding="utf-8") as fh:
            return json_module.load(fh)
    except FileNotFoundError:
        raise FileNotFoundError(
            "Exercise catalog snapshot not found; searched: " + ", ".join(str(path) for path in _CATALOG_SEARCH)
        ) from None


def seed_catalog(db: Session, catalog_path: str | None = None, snapshot: dict | None = None) -> int:
    """Upsert the catalog snapshot into the database. Returns the row count.

    Idempotent: existing wger ids are refreshed in place, new ones inserted.
    Rows that vanished upstream are intentionally kept (user plans may
    reference them); pass ``prune=True`` explicitly if ever needed.
    """
    if snapshot is None:
        snapshot = (
            load_snapshot()
            if catalog_path is None
            else json_module.loads(Path(catalog_path).read_text(encoding="utf-8"))
        )
    existing = {row.wger_id: row for row in db.scalars(select(ExerciseCatalog)).all()}
    for item in snapshot["exercises"]:
        translations = {
            tr["language"]: {"name": tr["name"], "description": tr["description"]} for tr in item["translations"]
        }
        en_name = translations.get("en", {}).get("name") or item["uuid"]
        row = existing.get(item["id"])
        if row is None:
            row = ExerciseCatalog(wger_id=item["id"])
            existing[item["id"]] = row
            db.add(row)
        row.uuid = item["uuid"]
        row.name = en_name
        row.translations = translations
        row.category_id = item["category"]
        row.equipment_ids = list(item["equipment"])
        row.muscle_ids = list(item["muscles"])
        row.muscle_ids_secondary = list(item["muscles_secondary"])
        row.variation_group = item.get("variation_group")
        row.license_author = item.get("license_author") or None
        row.aliases = item.get("aliases") or {}
        row.tips = item.get("tips") or {}
        row.license_name = item.get("license") or None
    db.commit()
    return len(snapshot["exercises"])
