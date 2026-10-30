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
import workouts.equipment_router as workouts_equipment_router
import workouts.feed as workouts_feed
import workouts.schema as workouts_schema
import workouts.wger_client as workouts_wger_client

router = APIRouter()

# Catalog and equipment endpoints must register before the /{plan_id} catch-all routes.
router.include_router(catalog_router.router, prefix="/exercises")
router.include_router(workouts_equipment_router.router, prefix="/equipment")


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
    # Opt-in mirror into the activity feed (publish_workouts_in_feed).
    try:
        workouts_feed.publish_session_activity(token_user_id, row, db)
    except Exception as e:
        import core.logger as core_logger

        core_logger.print_to_log(f"Feed publish for session {row.id} failed: {e}", "error", exc=e)
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
        return await workouts_ai_planner.generate_plan(
            db, settings, payload.prompt, payload.language, user_id=token_user_id
        )
    except (workouts_ai_planner.AiPlanError, nutrition_ai.AiAssistantError) as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e)) from e


# ---- on-demand exercise translation (RU descriptions for the info dialog) ----


def _strip_html(text: str) -> str:
    """Plain-text version of a wger HTML fragment (keeps the prompt small)."""
    import re

    no_tags = re.sub(r"<br\s*/?>", "\n", text)
    no_tags = re.sub(r"</p>", "\n\n", no_tags)
    no_tags = re.sub(r"<[^>]+>", "", no_tags)
    return re.sub(r"\n{3,}", "\n\n", no_tags).strip()


@router.post("/exercises/{wger_id}/translate", response_model=workouts_schema.ExerciseTranslation)
async def translate_catalog_exercise(
    wger_id: int,
    payload: workouts_schema.ExerciseTranslationRequest,
    _check_scopes: Annotated[Callable, Security(auth_dependencies.check_auth_scopes, scopes=["workouts:read"])],
    db: Annotated[Session, Depends(core_database.get_db)],
) -> workouts_schema.ExerciseTranslation:
    """Translate one catalog exercise's how-to + first tip via the shared AI provider.

    Stateless: nothing is written to the DB. The batch pipeline reuses this
    endpoint per exercise and stores results in
    ``backend/assets/exercise_descriptions_ru.json``.
    """
    from sqlalchemy import select

    import workouts.exercise_catalog as exercise_catalog

    settings = nutrition_ai.get_ai_settings(db)
    if not settings.configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI assistant is not configured. Ask your server administrator to enable it in server settings.",
        )
    row = db.scalars(
        select(exercise_catalog.ExerciseCatalog).where(exercise_catalog.ExerciseCatalog.wger_id == wger_id)
    ).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exercise not found in catalog")

    language = payload.language.strip() or "ru"
    en_desc = _strip_html(str(((row.translations or {}).get("en") or {}).get("description") or ""))[:2000]
    en_tips = (row.tips or {}).get("en") or []
    en_tip = _strip_html(str(en_tips[0]))[:500] if en_tips else ""
    if not en_desc and not en_tip:
        return workouts_schema.ExerciseTranslation(wger_id=wger_id, language=language)

    prompt = (
        "Translate the following fitness exercise description from English to Russian. "
        "Use correct Russian fitness terminology. Reply in EXACTLY this format with nothing else:\n"
        "DESCRIPTION: <translation, may span multiple lines>\n"
        "TIP: <translation or empty>\n\n"
        f"DESCRIPTION SOURCE:\n{en_desc or '(none)'}\n\nTIP SOURCE:\n{en_tip or '(none)'}"
    )
    try:
        reply = await nutrition_ai.chat_completion(
            settings.base_url,
            settings.api_key,
            settings.model,
            [{"role": "user", "content": prompt}],
        )
    except nutrition_ai.AiAssistantError as e:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(e)) from e

    description, tip = "", None
    current: str | None = None
    desc_lines: list[str] = []
    tip_lines: list[str] = []
    for line in reply.splitlines():
        stripped = line.strip()
        if stripped.upper().startswith("DESCRIPTION:"):
            current = "desc"
            desc_lines.append(stripped[len("DESCRIPTION:") :].strip())
        elif stripped.upper().startswith("TIP:"):
            current = "tip"
            tip_lines.append(stripped[len("TIP:") :].strip())
        elif current == "desc":
            desc_lines.append(line.rstrip())
        elif current == "tip":
            tip_lines.append(line.rstrip())
    description = "\n".join(desc_lines).strip()
    tip_text = "\n".join(tip_lines).strip()
    tip = tip_text or None
    return workouts_schema.ExerciseTranslation(wger_id=wger_id, language=language, description=description, tip=tip)


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
    # Look up the linked feed activity before the row disappears.
    session_row = workouts_crud.get_session(token_user_id, session_id, db)
    activity_id = session_row.activity_id
    workouts_crud.delete_session(token_user_id, session_id, db)
    if activity_id is not None:
        workouts_feed.delete_published_activity(activity_id, db)
