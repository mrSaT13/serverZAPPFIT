"""Competition endpoints under ``/competitions``.

Own domain (like workouts/nutrition): the mobile client syncs its local
Preparation tab here, and the web dashboard consumes ``/next`` for the
upcoming-race widget. All rows are scoped to the authenticated user.
"""

from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Security, status
from sqlalchemy.orm import Session

import auth.dependencies as auth_dependencies
import competitions.crud as competitions_crud
import competitions.schema as competitions_schema
import core.database as core_database

router = APIRouter()


@router.get("", response_model=list[competitions_schema.CompetitionRead])
async def list_competitions(
    _check_scopes: Annotated[Callable, Security(auth_dependencies.check_auth_scopes, scopes=["competitions:read"])],
    token_user_id: Annotated[int, Depends(auth_dependencies.get_user_id_from_auth)],
    db: Annotated[Session, Depends(core_database.get_db)],
    status_filter: Annotated[competitions_schema.CompetitionStatus | None, Query(alias="status")] = None,
) -> list[competitions_schema.CompetitionRead]:
    """The authenticated user's competitions, newest race day first."""
    rows = competitions_crud.list_competitions(token_user_id, db, status_filter=status_filter)
    return [competitions_schema.CompetitionRead.model_validate(r) for r in rows]


@router.get("/next", response_model=competitions_schema.NextCompetitionRead)
async def next_competition(
    _check_scopes: Annotated[Callable, Security(auth_dependencies.check_auth_scopes, scopes=["competitions:read"])],
    token_user_id: Annotated[int, Depends(auth_dependencies.get_user_id_from_auth)],
    db: Annotated[Session, Depends(core_database.get_db)],
) -> competitions_schema.NextCompetitionRead:
    """Next upcoming race + readiness estimate (never 404s; ``competition: null`` when none)."""
    row = competitions_crud.get_next_competition(token_user_id, db)
    if row is None:
        return competitions_schema.NextCompetitionRead(
            days_left=0, avg_weekly_km=0.0, required_weekly_km=0.0, readiness=0.0
        )
    return competitions_crud.readiness_snapshot(token_user_id, row, db)


@router.post("", response_model=competitions_schema.CompetitionRead, status_code=status.HTTP_201_CREATED)
async def create_competition(
    payload: competitions_schema.CompetitionCreate,
    _check_scopes: Annotated[Callable, Security(auth_dependencies.check_auth_scopes, scopes=["competitions:write"])],
    token_user_id: Annotated[int, Depends(auth_dependencies.get_user_id_from_auth)],
    db: Annotated[Session, Depends(core_database.get_db)],
) -> competitions_schema.CompetitionRead:
    """Add a competition (from the web dashboard or the mobile Preparation tab)."""
    row = competitions_crud.create_competition(token_user_id, payload, db)
    return competitions_schema.CompetitionRead.model_validate(row)


@router.get("/{competition_id}", response_model=competitions_schema.CompetitionRead)
async def get_competition(
    competition_id: int,
    _check_scopes: Annotated[Callable, Security(auth_dependencies.check_auth_scopes, scopes=["competitions:read"])],
    token_user_id: Annotated[int, Depends(auth_dependencies.get_user_id_from_auth)],
    db: Annotated[Session, Depends(core_database.get_db)],
) -> competitions_schema.CompetitionRead:
    row = competitions_crud.get_competition(token_user_id, competition_id, db)
    return competitions_schema.CompetitionRead.model_validate(row)


@router.put("/{competition_id}", response_model=competitions_schema.CompetitionRead)
async def update_competition(
    competition_id: int,
    payload: competitions_schema.CompetitionUpdate,
    _check_scopes: Annotated[Callable, Security(auth_dependencies.check_auth_scopes, scopes=["competitions:write"])],
    token_user_id: Annotated[int, Depends(auth_dependencies.get_user_id_from_auth)],
    db: Annotated[Session, Depends(core_database.get_db)],
) -> competitions_schema.CompetitionRead:
    """Update a competition; results (place/time) arrive here when raced."""
    row = competitions_crud.update_competition(token_user_id, competition_id, payload, db)
    return competitions_schema.CompetitionRead.model_validate(row)


@router.delete("/{competition_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_competition(
    competition_id: int,
    _check_scopes: Annotated[Callable, Security(auth_dependencies.check_auth_scopes, scopes=["competitions:write"])],
    token_user_id: Annotated[int, Depends(auth_dependencies.get_user_id_from_auth)],
    db: Annotated[Session, Depends(core_database.get_db)],
) -> None:
    competitions_crud.delete_competition(token_user_id, competition_id, db)
