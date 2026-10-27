"""Catalog endpoints (baked wger exercise data) under /workouts/exercises."""

from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Security, status
from pydantic import BaseModel, ConfigDict, StrictInt, StrictStr
from sqlalchemy import func, select
from sqlalchemy.orm import Session

import auth.dependencies as auth_dependencies
import core.database as core_database
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
    )


@router.get("", response_model=CatalogExerciseListResponse)
async def search_catalog(
    _check_scopes: Annotated[
        Callable, Security(auth_dependencies.check_auth_scopes, scopes=["workouts:read"])
    ],
    q: Annotated[str | None, Query(max_length=100)] = None,
    category_id: Annotated[int | None, Query()] = None,
    equipment_id: Annotated[int | None, Query()] = None,
    muscle_id: Annotated[int | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    offset: Annotated[int, Query(ge=0)] = 0,
    db: Annotated[Session, Depends(core_database.get_db)] = None,  # type: ignore[assignment]
) -> CatalogExerciseListResponse:
    """Search the offline exercise catalog by name/category/equipment/muscle."""
    filters = []
    if q:
        filters.append(exercise_catalog.ExerciseCatalog.name.ilike(f"%{q}%"))
    if category_id is not None:
        filters.append(exercise_catalog.ExerciseCatalog.category_id == category_id)
    # JSON columns are searched in memory (catalog is small, ~875 rows).
    rows = db.scalars(select(exercise_catalog.ExerciseCatalog).where(*filters)).all()
    matched = [
        r
        for r in rows
        if (equipment_id is None or equipment_id in (r.equipment_ids or []))
        and (muscle_id is None or muscle_id in (r.muscle_ids or []))
    ]
    matched.sort(key=lambda r: r.name.lower())
    total = len(matched)
    snapshot = exercise_catalog.load_snapshot()
    return CatalogExerciseListResponse(
        total=total,
        records=[_to_read(r, snapshot) for r in matched[offset : offset + limit]],
    )


@router.get("/meta", response_model=CatalogMetaResponse)
async def catalog_meta(
    _check_scopes: Annotated[
        Callable, Security(auth_dependencies.check_auth_scopes, scopes=["workouts:read"])
    ],
    db: Annotated[Session, Depends(core_database.get_db)] = None,  # type: ignore[assignment]
) -> CatalogMetaResponse:
    """Filter dictionaries + counts for the picker UI (one call on page load)."""
    snapshot = exercise_catalog.load_snapshot()
    total = db.scalars(select(func.count()).select_from(exercise_catalog.ExerciseCatalog)).one()
    empty = total == 0
    return CatalogMetaResponse(
        counts={"exercises": int(total), "seedError": 1 if empty else 0},
        categories=snapshot["categories"],
        equipment=snapshot["equipment"],
        muscles=snapshot["muscles"],
    )


@router.get("/{wger_id}", response_model=CatalogExerciseRead)
async def get_catalog_exercise(
    wger_id: int,
    _check_scopes: Annotated[
        Callable, Security(auth_dependencies.check_auth_scopes, scopes=["workouts:read"])
    ],
    db: Annotated[Session, Depends(core_database.get_db)] = None,  # type: ignore[assignment]
) -> CatalogExerciseRead:
    row = db.scalars(
        select(exercise_catalog.ExerciseCatalog).where(exercise_catalog.ExerciseCatalog.wger_id == wger_id)
    ).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exercise not found in catalog")
    return _to_read(row, exercise_catalog.load_snapshot())
