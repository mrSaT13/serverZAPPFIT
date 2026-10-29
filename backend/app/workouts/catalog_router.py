"""Catalog endpoints (baked wger exercise data) under /workouts/exercises."""

from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Security, status
from pydantic import BaseModel, ConfigDict, StrictInt, StrictStr
from sqlalchemy import func, select
from sqlalchemy.orm import Session

import auth.dependencies as auth_dependencies
import core.database as core_database
import core.logger as core_logger
import workouts.exercise_catalog as exercise_catalog


class TranslationRead(BaseModel):
    name: StrictStr
    description: StrictStr = ""


class CatalogExerciseRead(BaseModel):
    """Catalog row + related-dictionary entries resolved to labels."""

    wger_id: StrictInt
    uuid: StrictStr
    name: StrictStr
    translations: dict[str, TranslationRead]
    category: dict | None = None
    muscles: list[dict] = []
    muscles_secondary: list[dict] = []
    equipment: list[dict] = []
    variation_group: StrictStr | None = None
    license_author: StrictStr | None = None
    license: StrictStr | None = None
    # language code -> alternative names (search synonyms) / technique tips
    aliases: dict[str, list[StrictStr]] = {}
    tips: dict[str, list[StrictStr]] = {}

    model_config = ConfigDict(from_attributes=True)


class CatalogExerciseListResponse(BaseModel):
    total: StrictInt
    records: list[CatalogExerciseRead]


class CatalogMetaResponse(BaseModel):
    counts: dict[str, int]
    categories: list[dict]
    equipment: list[dict]
    muscles: list[dict]


router = APIRouter()


def _dictionaries(snapshot: dict) -> tuple[dict, dict, dict]:
    categories = {c["id"]: c for c in snapshot["categories"]}
    equipment = {e["id"]: e for e in snapshot["equipment"]}
    muscles = {m["id"]: m for m in snapshot["muscles"]}
    return categories, equipment, muscles


def _to_read(row: exercise_catalog.ExerciseCatalog, snapshot: dict) -> CatalogExerciseRead:
    categories, equipment, muscles = _dictionaries(snapshot)
    return CatalogExerciseRead(
        wger_id=row.wger_id,
        uuid=row.uuid,
        name=row.name,
        translations=row.translations or {},
        category=categories.get(row.category_id),
        muscles=[muscles[i] for i in row.muscle_ids or [] if i in muscles],
        muscles_secondary=[muscles[i] for i in row.muscle_ids_secondary or [] if i in muscles],
        equipment=[equipment[i] for i in row.equipment_ids or [] if i in equipment],
        variation_group=row.variation_group,
        license_author=row.license_author,
        license=row.license_name,
        aliases=row.aliases or {},
        tips=row.tips or {},
    )


def _snapshot_or_none() -> dict | None:
    """Load the bundled snapshot, or ``None`` when the asset is unavailable.

    A missing snapshot used to 500 both catalog endpoints, which left the
    picker with an empty list and no explanation. Instead the endpoints keep
    working and ``/meta`` reports ``seedError: 1`` so the UI can show a clear
    "catalog not seeded" hint.
    """
    try:
        return exercise_catalog.load_snapshot()
    except Exception as e:  # pragma: no cover — only hit on broken deployments
        core_logger.print_to_log(f"Exercise catalog snapshot unavailable: {e}", "error", exc=e)
        return None


def _matches_query(row: exercise_catalog.ExerciseCatalog, q_lower: str, lang: str | None = None) -> bool:
    """Name match scoped to the requested display language.

    Without ``lang`` every translation and alias is checked (legacy
    behaviour). With ``lang`` only that language's translated name and
    aliases are matched — plus the canonical English name, which stays the
    stable identity of a row, so "bench press" keeps working in a Russian UI
    while "жим" no longer leaks into an English search. When a translation is
    missing in ``lang`` the row displays its English name, so that name is
    searched instead (search always sees what the UI shows).
    """
    if q_lower in row.name.lower():
        return True
    if lang:
        tr = (row.translations or {}).get(lang)
        name = tr.get("name") if isinstance(tr, dict) else None
        if name and q_lower in str(name).lower():
            return True
        return any(q_lower in str(alias).lower() for alias in (row.aliases or {}).get(lang, []))
    for tr in (row.translations or {}).values():
        name = tr.get("name") if isinstance(tr, dict) else None
        if name and q_lower in str(name).lower():
            return True
    for alias_list in (row.aliases or {}).values():
        if any(q_lower in str(alias).lower() for alias in alias_list):
            return True
    return False


def _display_name(row: exercise_catalog.ExerciseCatalog, lang: str | None) -> str:
    """Row name as the UI shows it in ``lang`` (English fallback)."""
    if lang:
        tr = (row.translations or {}).get(lang)
        name = tr.get("name") if isinstance(tr, dict) else None
        if name:
            return str(name)
    return row.name


@router.get("", response_model=CatalogExerciseListResponse)
async def search_catalog(
    _check_scopes: Annotated[Callable, Security(auth_dependencies.check_auth_scopes, scopes=["workouts:read"])],
    q: Annotated[str | None, Query(max_length=100)] = None,
    category_id: Annotated[int | None, Query()] = None,
    equipment_id: Annotated[int | None, Query()] = None,
    muscle_id: Annotated[int | None, Query()] = None,
    lang: Annotated[str | None, Query(max_length=10, description="Scope search & sort to this UI language")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
    db: Annotated[Session, Depends(core_database.get_db)] = None,  # type: ignore[assignment]
) -> CatalogExerciseListResponse:
    """Search the offline exercise catalog by name/category/equipment/muscle."""
    snapshot = _snapshot_or_none()
    if snapshot is None:
        return CatalogExerciseListResponse(total=0, records=[])
    filters = []
    if category_id is not None:
        filters.append(exercise_catalog.ExerciseCatalog.category_id == category_id)
    # JSON columns are searched in memory (catalog is small, ~915 rows).
    rows = db.scalars(select(exercise_catalog.ExerciseCatalog).where(*filters)).all()
    q_lower = q.lower().strip() if q else None
    matched = [
        r
        for r in rows
        if (q_lower is None or _matches_query(r, q_lower, lang))
        and (equipment_id is None or equipment_id in (r.equipment_ids or []))
        and (muscle_id is None or muscle_id in (r.muscle_ids or []))
    ]
    # Sort by the name the user actually sees in their language.
    matched.sort(key=lambda r: _display_name(r, lang).lower())
    total = len(matched)
    return CatalogExerciseListResponse(
        total=total,
        records=[_to_read(r, snapshot) for r in matched[offset : offset + limit]],
    )


@router.get("/meta", response_model=CatalogMetaResponse)
async def catalog_meta(
    _check_scopes: Annotated[Callable, Security(auth_dependencies.check_auth_scopes, scopes=["workouts:read"])],
    db: Annotated[Session, Depends(core_database.get_db)] = None,  # type: ignore[assignment]
) -> CatalogMetaResponse:
    """Filter dictionaries + counts for the picker UI (one call on page load)."""
    snapshot = _snapshot_or_none()
    total = db.scalars(select(func.count()).select_from(exercise_catalog.ExerciseCatalog)).one()
    broken = snapshot is None or total == 0
    return CatalogMetaResponse(
        counts={"exercises": int(total), "seedError": 1 if broken else 0},
        categories=snapshot["categories"] if snapshot else [],
        equipment=snapshot["equipment"] if snapshot else [],
        muscles=snapshot["muscles"] if snapshot else [],
    )


@router.get("/{wger_id}", response_model=CatalogExerciseRead)
async def get_catalog_exercise(
    wger_id: int,
    _check_scopes: Annotated[Callable, Security(auth_dependencies.check_auth_scopes, scopes=["workouts:read"])],
    db: Annotated[Session, Depends(core_database.get_db)] = None,  # type: ignore[assignment]
) -> CatalogExerciseRead:
    row = db.scalars(
        select(exercise_catalog.ExerciseCatalog).where(exercise_catalog.ExerciseCatalog.wger_id == wger_id)
    ).first()
    snapshot = _snapshot_or_none()
    if not row or snapshot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exercise not found in catalog")
    return _to_read(row, snapshot)
