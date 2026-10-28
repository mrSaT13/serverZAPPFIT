"""CRUD for meal_logs."""

from datetime import date as date_type

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

import core.decorators as core_decorators
import nutrition.models as nutrition_models
import nutrition.schema as nutrition_schema


def _parse_date(value: str | date_type) -> date_type:
    """Normalise a query date to a real date object.

    Postgres refuses ``Date >= VARCHAR`` (unlike SQLite, which silently
    coerced strings), so date filters must be typed before hitting the DB.
    """
    return value if isinstance(value, date_type) else date_type.fromisoformat(str(value))


@core_decorators.handle_db_errors
def list_meal_logs(
    user_id: int, date_from: str | None, date_to: str | None, db: Session
) -> list[nutrition_models.MealLog]:
    stmt = (
        select(nutrition_models.MealLog)
        .where(nutrition_models.MealLog.user_id == user_id)
        .order_by(nutrition_models.MealLog.date.desc(), nutrition_models.MealLog.id.desc())
    )
    if date_from:
        stmt = stmt.where(nutrition_models.MealLog.date >= _parse_date(date_from))
    if date_to:
        stmt = stmt.where(nutrition_models.MealLog.date <= _parse_date(date_to))
    return list(db.scalars(stmt).all())


@core_decorators.handle_db_errors
def create_meal_log(user_id: int, payload: nutrition_schema.MealLogCreate, db: Session) -> nutrition_models.MealLog:
    row = nutrition_models.MealLog(user_id=user_id, **payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@core_decorators.handle_db_errors
def update_meal_log(user_id: int, payload: nutrition_schema.MealLogUpdate, db: Session) -> nutrition_models.MealLog:
    stmt = select(nutrition_models.MealLog).where(
        nutrition_models.MealLog.id == payload.id, nutrition_models.MealLog.user_id == user_id
    )
    row = db.scalars(stmt).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meal log not found")
    for k, v in payload.model_dump(exclude={"id"}).items():
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return row


@core_decorators.handle_db_errors
def delete_meal_log(user_id: int, log_id: int, db: Session) -> None:
    stmt = select(nutrition_models.MealLog).where(
        nutrition_models.MealLog.id == log_id, nutrition_models.MealLog.user_id == user_id
    )
    row = db.scalars(stmt).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meal log not found")
    db.delete(row)
    db.commit()


@core_decorators.handle_db_errors
def summary_for_date(user_id: int, target_date: str, db: Session) -> dict:
    from sqlalchemy import func as sa_func

    stmt = select(
        sa_func.coalesce(sa_func.sum(nutrition_models.MealLog.calories), 0),
        sa_func.coalesce(sa_func.sum(nutrition_models.MealLog.protein), 0),
        sa_func.coalesce(sa_func.sum(nutrition_models.MealLog.carbs), 0),
        sa_func.coalesce(sa_func.sum(nutrition_models.MealLog.fat), 0),
    ).where(nutrition_models.MealLog.user_id == user_id, nutrition_models.MealLog.date == _parse_date(target_date))
    cals, prot, carbs, fat = db.execute(stmt).one()
    return {
        "calories": float(cals or 0),
        "protein": float(prot or 0),
        "carbs": float(carbs or 0),
        "fat": float(fat or 0),
    }


@core_decorators.handle_db_errors
def daily_totals(user_id: int, date_from: str, date_to: str, db: Session) -> list[dict]:
    """Per-day intake totals (SQL group-by) for the nutrition trend charts."""
    from sqlalchemy import func as sa_func

    stmt = (
        select(
            nutrition_models.MealLog.date,
            sa_func.coalesce(sa_func.sum(nutrition_models.MealLog.calories), 0),
            sa_func.coalesce(sa_func.sum(nutrition_models.MealLog.protein), 0),
            sa_func.coalesce(sa_func.sum(nutrition_models.MealLog.carbs), 0),
            sa_func.coalesce(sa_func.sum(nutrition_models.MealLog.fat), 0),
        )
        .where(
            nutrition_models.MealLog.user_id == user_id,
            nutrition_models.MealLog.date >= _parse_date(date_from),
            nutrition_models.MealLog.date <= _parse_date(date_to),
        )
        .group_by(nutrition_models.MealLog.date)
        .order_by(nutrition_models.MealLog.date)
    )
    rows = db.execute(stmt).all()
    return [
        {
            "date": row_date,
            "calories": float(cals or 0),
            "protein": float(prot or 0),
            "carbs": float(carbs or 0),
            "fat": float(fat or 0),
        }
        for row_date, cals, prot, carbs, fat in rows
    ]
