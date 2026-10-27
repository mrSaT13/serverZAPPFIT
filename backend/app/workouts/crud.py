"""CRUD for workout plans, sessions and exercise progress."""

from datetime import date as date_type

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

import core.decorators as core_decorators
import workouts.models as workouts_models
import workouts.schema as workouts_schema


# ---- plans ----


@core_decorators.handle_db_errors
def list_plans(user_id: int, db: Session) -> list[workouts_models.WorkoutPlan]:
    stmt = (
        select(workouts_models.WorkoutPlan)
        .where(workouts_models.WorkoutPlan.user_id == user_id)
        .options(selectinload(workouts_models.WorkoutPlan.exercises))
        .order_by(workouts_models.WorkoutPlan.created_at.desc())
    )
    return list(db.scalars(stmt).all())


@core_decorators.handle_db_errors
def get_plan(user_id: int, plan_id: int, db: Session) -> workouts_models.WorkoutPlan:
    stmt = (
        select(workouts_models.WorkoutPlan)
        .where(workouts_models.WorkoutPlan.id == plan_id, workouts_models.WorkoutPlan.user_id == user_id)
        .options(selectinload(workouts_models.WorkoutPlan.exercises))
    )
    row = db.scalars(stmt).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workout plan not found")
    return row


@core_decorators.handle_db_errors
def create_plan(
    user_id: int, payload: workouts_schema.WorkoutPlanCreate, db: Session, source: str = "manual", wger_plan_id: int | None = None
) -> workouts_models.WorkoutPlan:
    row = workouts_models.WorkoutPlan(user_id=user_id, name=payload.name, description=payload.description, source=source, wger_plan_id=wger_plan_id)
    row.exercises = [
        workouts_models.WorkoutExercise(**ex.model_dump()) for ex in payload.exercises
    ]
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@core_decorators.handle_db_errors
def update_plan(
    user_id: int, plan_id: int, payload: workouts_schema.WorkoutPlanUpdate, db: Session
) -> workouts_models.WorkoutPlan:
    row = get_plan(user_id, plan_id, db)
    row.name = payload.name
    row.description = payload.description
    row.exercises = [workouts_models.WorkoutExercise(**ex.model_dump()) for ex in payload.exercises]
    db.commit()
    db.refresh(row)
    return row


@core_decorators.handle_db_errors
def delete_plan(user_id: int, plan_id: int, db: Session) -> None:
    row = get_plan(user_id, plan_id, db)
    db.delete(row)
    db.commit()


# ---- sessions ----


@core_decorators.handle_db_errors
def list_sessions(
    user_id: int, date_from: str | None, date_to: str | None, db: Session
) -> list[workouts_models.WorkoutSession]:
    stmt = (
        select(workouts_models.WorkoutSession)
        .where(workouts_models.WorkoutSession.user_id == user_id)
        .options(selectinload(workouts_models.WorkoutSession.sets))
        .order_by(workouts_models.WorkoutSession.date.desc(), workouts_models.WorkoutSession.id.desc())
    )
    # Postgres refuses `Date >= VARCHAR` — normalise filter strings to dates.
    if date_from:
        stmt = stmt.where(workouts_models.WorkoutSession.date >= date_type.fromisoformat(str(date_from)))
    if date_to:
        stmt = stmt.where(workouts_models.WorkoutSession.date <= date_type.fromisoformat(str(date_to)))
    return list(db.scalars(stmt).all())


@core_decorators.handle_db_errors
def get_session(user_id: int, session_id: int, db: Session) -> workouts_models.WorkoutSession:
    stmt = (
        select(workouts_models.WorkoutSession)
        .where(
            workouts_models.WorkoutSession.id == session_id,
            workouts_models.WorkoutSession.user_id == user_id,
        )
        .options(selectinload(workouts_models.WorkoutSession.sets))
    )
    row = db.scalars(stmt).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workout session not found")
    return row


@core_decorators.handle_db_errors
def create_session(
    user_id: int, payload: workouts_schema.WorkoutSessionCreate, db: Session
) -> workouts_models.WorkoutSession:
    if payload.plan_id is not None:
        get_plan(user_id, payload.plan_id, db)
    row = workouts_models.WorkoutSession(
        user_id=user_id,
        date=payload.date,
        plan_id=payload.plan_id,
        duration_min=payload.duration_min,
        calories=payload.calories,
        comment=payload.comment,
    )
    row.sets = [workouts_models.WorkoutSetLog(**s.model_dump()) for s in payload.sets]
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@core_decorators.handle_db_errors
def delete_session(user_id: int, session_id: int, db: Session) -> None:
    row = get_session(user_id, session_id, db)
    db.delete(row)
    db.commit()


# ---- progress ----


def _epley(weight: float, reps: int) -> float:
    return weight * (1 + reps / 30) if weight and reps else (weight or 0)


@core_decorators.handle_db_errors
def exercise_progress(
    user_id: int, exercise_name: str, db: Session
) -> workouts_schema.ExerciseProgress:
    stmt = (
        select(workouts_models.WorkoutSession)
        .where(
            workouts_models.WorkoutSession.user_id == user_id,
            workouts_models.WorkoutSession.sets.any(
                workouts_models.WorkoutSetLog.exercise_name == exercise_name
            ),
        )
        .options(selectinload(workouts_models.WorkoutSession.sets))
        .order_by(workouts_models.WorkoutSession.date.asc())
    )
    sessions = list(db.scalars(stmt).all())

    out = workouts_schema.ExerciseProgress(exercise_name=exercise_name)
    wger_id = None
    for s in sessions:
        logged = [x for x in s.sets if x.exercise_name == exercise_name and x.completed]
        if not logged:
            continue
        if wger_id is None:
            wger_id = next((x.wger_exercise_id for x in logged if x.wger_exercise_id is not None), None)
        best = max(logged, key=lambda x: (x.weight_kg or 0, x.reps or 0))
        points = workouts_schema.ExercisePoint(
            date=s.date,
            best_weight_kg=best.weight_kg,
            best_reps=best.reps,
            est_1rm=_epley(best.weight_kg or 0, best.reps or 0) if best.weight_kg and best.reps else None,
            total_volume=sum((x.weight_kg or 0) * (x.reps or 0) for x in logged),
        )
        out.points.append(points)
        out.sessions += 1
        if points.best_weight_kg is not None and (out.best_weight_kg is None or points.best_weight_kg > out.best_weight_kg):
            out.best_weight_kg = points.best_weight_kg
        if points.est_1rm is not None and (out.best_est_1rm is None or points.est_1rm > out.best_est_1rm):
            out.best_est_1rm = points.est_1rm
    out.wger_exercise_id = wger_id
    return out


@core_decorators.handle_db_errors
def distinct_exercises(user_id: int, db: Session) -> list[str]:
    stmt = (
        select(workouts_models.WorkoutSetLog.exercise_name)
        .join(workouts_models.WorkoutSession, workouts_models.WorkoutSetLog.session_id == workouts_models.WorkoutSession.id)
        .where(workouts_models.WorkoutSession.user_id == user_id)
        .group_by(workouts_models.WorkoutSetLog.exercise_name)
        .order_by(func.count(workouts_models.WorkoutSetLog.id).desc())
    )
    return list(db.scalars(stmt).all())
