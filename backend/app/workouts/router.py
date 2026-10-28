"""Workouts router — strength-training plans, sessions and progress."""

from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Security, status
from sqlalchemy.orm import Session

import auth.dependencies as auth_dependencies
import core.database as core_database
import nutrition.ai as nutrition_ai
import workouts.ai_planner as workouts_ai_planner
import workouts.catalog_router as catalog_router
import workouts.crud as workouts_crud
import workouts.schema as workouts_schema
import workouts.wger_client as workouts_wger_client

router = APIRouter()

# Catalog endpoints must register before the /{plan_id} catch-all routes.
router.include_router(catalog_router.router, prefix="/exercises")


@router.get("", response_model=list[workouts_schema.WorkoutPlanRead])
async def list_workout_plans(
    _check_scopes: Annotated[Callable, Security(auth_dependencies.check_auth_scopes, scopes=["workouts:read"])],
    token_user_id: Annotated[int, Depends(auth_dependencies.get_user_id_from_auth)],
    db: Annotated[Session, Depends(core_database.get_db)],
) -> list[workouts_schema.WorkoutPlanRead]:
    rows = workouts_crud.list_plans(token_user_id, db)
    return [workouts_schema.WorkoutPlanRead.model_validate(r) for r in rows]


@router.post("", response_model=workouts_schema.WorkoutPlanRead, status_code=status.HTTP_201_CREATED)
async def create_workout_plan(
    payload: workouts_schema.WorkoutPlanCreate,
    _check_scopes: Annotated[Callable, Security(auth_dependencies.check_auth_scopes, scopes=["workouts:write"])],
    token_user_id: Annotated[int, Depends(auth_dependencies.get_user_id_from_auth)],
    db: Annotated[Session, Depends(core_database.get_db)],
) -> workouts_schema.WorkoutPlanRead:
    row = workouts_crud.create_plan(token_user_id, payload, db)
    return workouts_schema.WorkoutPlanRead.model_validate(row)


@router.get("/sessions", response_model=list[workouts_schema.WorkoutSessionRead])
async def list_workout_sessions(
    _check_scopes: Annotated[Callable, Security(auth_dependencies.check_auth_scopes, scopes=["workouts:read"])],
    token_user_id: Annotated[int, Depends(auth_dependencies.get_user_id_from_auth)],
    db: Annotated[Session, Depends(core_database.get_db)],
    date_from: Annotated[str | None, Query()] = None,
    date_to: Annotated[str | None, Query()] = None,
) -> list[workouts_schema.WorkoutSessionRead]:
    rows = workouts_crud.list_sessions(token_user_id, date_from, date_to, db)
    return [workouts_schema.WorkoutSessionRead.model_validate(r) for r in rows]


@router.post("/sessions", response_model=workouts_schema.WorkoutSessionRead, status_code=status.HTTP_201_CREATED)
async def create_workout_session(
    payload: workouts_schema.WorkoutSessionCreate,
    _check_scopes: Annotated[Callable, Security(auth_dependencies.check_auth_scopes, scopes=["workouts:write"])],
    token_user_id: Annotated[int, Depends(auth_dependencies.get_user_id_from_auth)],
    db: Annotated[Session, Depends(core_database.get_db)],
) -> workouts_schema.WorkoutSessionRead:
    row = workouts_crud.create_session(token_user_id, payload, db)
    return workouts_schema.WorkoutSessionRead.model_validate(row)


@router.get("/statistics", response_model=workouts_schema.WorkoutStatistics)
async def get_workout_statistics(
    _check_scopes: Annotated[Callable, Security(auth_dependencies.check_auth_scopes, scopes=["workouts:read"])],
    token_user_id: Annotated[int, Depends(auth_dependencies.get_user_id_from_auth)],
    db: Annotated[Session, Depends(core_database.get_db)],
    date_from: Annotated[str | None, Query()] = None,
    date_to: Annotated[str | None, Query()] = None,
) -> workouts_schema.WorkoutStatistics:
    """Weekly aggregates for the workouts page charts (range capped at 366 days)."""
    return workouts_crud.weekly_statistics(token_user_id, date_from, date_to, db)


@router.get("/progress", response_model=list[workouts_schema.ExerciseProgress])
async def list_exercises_progress(
    _check_scopes: Annotated[Callable, Security(auth_dependencies.check_auth_scopes, scopes=["workouts:read"])],
    token_user_id: Annotated[int, Depends(auth_dependencies.get_user_id_from_auth)],
    db: Annotated[Session, Depends(core_database.get_db)],
) -> list[workouts_schema.ExerciseProgress]:
    """Progress for every logged exercise, best-per-session points included."""
    return [
        workouts_crud.exercise_progress(token_user_id, name, db)
        for name in workouts_crud.distinct_exercises(token_user_id, db)
    ]


@router.get("/progress/{exercise_name:path}", response_model=workouts_schema.ExerciseProgress)
async def get_exercise_progress(
    exercise_name: str,
    _check_scopes: Annotated[Callable, Security(auth_dependencies.check_auth_scopes, scopes=["workouts:read"])],
    token_user_id: Annotated[int, Depends(auth_dependencies.get_user_id_from_auth)],
    db: Annotated[Session, Depends(core_database.get_db)],
) -> workouts_schema.ExerciseProgress:
    return workouts_crud.exercise_progress(token_user_id, exercise_name, db)


# ---- AI plan generator (same provider settings as the nutrition assistant) ----


@router.get("/ai/status", response_model=workouts_schema.AiStatusRead)
async def ai_status(
    _check_scopes: Annotated[Callable, Security(auth_dependencies.check_auth_scopes, scopes=["workouts:read"])],
    db: Annotated[Session, Depends(core_database.get_db)],
) -> workouts_schema.AiStatusRead:
    """Tell the UI whether the AI plan generator is available."""
    settings = nutrition_ai.get_ai_settings(db)
    return workouts_schema.AiStatusRead(enabled=settings.enabled, configured=settings.configured, model=settings.model)


@router.post("/ai/plan", response_model=workouts_schema.AiPlanDraft)
async def generate_ai_plan(
    payload: workouts_schema.AiPlanGenerateRequest,
    _check_scopes: Annotated[Callable, Security(auth_dependencies.check_auth_scopes, scopes=["workouts:read"])],
    token_user_id: Annotated[int, Depends(auth_dependencies.get_user_id_from_auth)],
    db: Annotated[Session, Depends(core_database.get_db)],
) -> workouts_schema.AiPlanDraft:
    """Turn a free-text goal into a plan draft built from the offline catalog.

    Read-only: the draft is returned to the client's plan editor and is only
    persisted when the user saves it via the normal ``POST /workouts``.
    """
    settings = nutrition_ai.get_ai_settings(db)
    if not settings.configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI assistant is not configured. Ask your server administrator to enable it in server settings.",
        )
    try:
        return await workouts_ai_planner.generate_plan(db, settings, payload.prompt, payload.language)
    except (workouts_ai_planner.AiPlanError, nutrition_ai.AiAssistantError) as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e)) from e


# ---- wger import ----


@router.get("/import/wger", response_model=list[workouts_schema.WgerRoutinePreview])
async def preview_wger_routines(
    _check_scopes: Annotated[Callable, Security(auth_dependencies.check_auth_scopes, scopes=["workouts:read"])],
    token_user_id: Annotated[int, Depends(auth_dependencies.get_user_id_from_auth)],
    db: Annotated[Session, Depends(core_database.get_db)],
) -> list[workouts_schema.WgerRoutinePreview]:
    try:
        return workouts_wger_client.list_routines(token_user_id, db)
    except workouts_wger_client.WgerImportError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e)) from e


@router.post(
    "/import/wger/{wger_routine_id}",
    response_model=workouts_schema.WorkoutPlanRead,
    status_code=status.HTTP_201_CREATED,
)
async def import_wger_routine(
    wger_routine_id: int,
    _check_scopes: Annotated[Callable, Security(auth_dependencies.check_auth_scopes, scopes=["workouts:write"])],
    token_user_id: Annotated[int, Depends(auth_dependencies.get_user_id_from_auth)],
    db: Annotated[Session, Depends(core_database.get_db)],
) -> workouts_schema.WorkoutPlanRead:
    try:
        payload = workouts_wger_client.import_routine(token_user_id, db, wger_routine_id)
    except workouts_wger_client.WgerImportError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e)) from e
    row = workouts_crud.create_plan(token_user_id, payload, db, source="wger", wger_plan_id=wger_routine_id)
    return workouts_schema.WorkoutPlanRead.model_validate(row)


@router.get("/{plan_id}", response_model=workouts_schema.WorkoutPlanRead)
async def get_workout_plan(
    plan_id: int,
    _check_scopes: Annotated[Callable, Security(auth_dependencies.check_auth_scopes, scopes=["workouts:read"])],
    token_user_id: Annotated[int, Depends(auth_dependencies.get_user_id_from_auth)],
    db: Annotated[Session, Depends(core_database.get_db)],
) -> workouts_schema.WorkoutPlanRead:
    return workouts_schema.WorkoutPlanRead.model_validate(workouts_crud.get_plan(token_user_id, plan_id, db))


@router.put("/{plan_id}", response_model=workouts_schema.WorkoutPlanRead)
async def update_workout_plan(
    plan_id: int,
    payload: workouts_schema.WorkoutPlanUpdate,
    _check_scopes: Annotated[Callable, Security(auth_dependencies.check_auth_scopes, scopes=["workouts:write"])],
    token_user_id: Annotated[int, Depends(auth_dependencies.get_user_id_from_auth)],
    db: Annotated[Session, Depends(core_database.get_db)],
) -> workouts_schema.WorkoutPlanRead:
    row = workouts_crud.update_plan(token_user_id, plan_id, payload, db)
    return workouts_schema.WorkoutPlanRead.model_validate(row)


@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workout_plan(
    plan_id: int,
    _check_scopes: Annotated[Callable, Security(auth_dependencies.check_auth_scopes, scopes=["workouts:write"])],
    token_user_id: Annotated[int, Depends(auth_dependencies.get_user_id_from_auth)],
    db: Annotated[Session, Depends(core_database.get_db)],
) -> None:
    workouts_crud.delete_plan(token_user_id, plan_id, db)


@router.get("/sessions/{session_id}", response_model=workouts_schema.WorkoutSessionRead)
async def get_workout_session(
    session_id: int,
    _check_scopes: Annotated[Callable, Security(auth_dependencies.check_auth_scopes, scopes=["workouts:read"])],
    token_user_id: Annotated[int, Depends(auth_dependencies.get_user_id_from_auth)],
    db: Annotated[Session, Depends(core_database.get_db)],
) -> workouts_schema.WorkoutSessionRead:
    return workouts_schema.WorkoutSessionRead.model_validate(workouts_crud.get_session(token_user_id, session_id, db))


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workout_session(
    session_id: int,
    _check_scopes: Annotated[Callable, Security(auth_dependencies.check_auth_scopes, scopes=["workouts:write"])],
    token_user_id: Annotated[int, Depends(auth_dependencies.get_user_id_from_auth)],
    db: Annotated[Session, Depends(core_database.get_db)],
) -> None:
    workouts_crud.delete_session(token_user_id, session_id, db)
