"""CRUD for competitions + the training-readiness estimate.

The readiness formula mirrors the mobile client's Preparation tab
(``preparation_tab.dart``) so the web dashboard and the phone agree:
rolling-28-day average weekly distance (all logged activities, distance in
metres / 4 weeks) compared against the weekly load a race of this length
expects (5 km → 20, 10 km → 30, half → 45, marathon+ → 60 km/week).
"""

from datetime import date, timedelta

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

import activities.activity.models as activities_models
import competitions.models as competitions_models
import competitions.schema as competitions_schema
import core.decorators as core_decorators

_TRACKING_WINDOW_DAYS = 28
_WEEKS_IN_WINDOW = 4


def _required_weekly_km(distance_km: float) -> int:
    """Weekly distance a race of this length expects (client thresholds)."""
    if distance_km <= 5:
        return 20
    if distance_km <= 10:
        return 30
    if distance_km <= 21.5:  # half marathon is 21.0975 km
        return 45
    return 60


@core_decorators.handle_db_errors
def list_competitions(
    user_id: int,
    db: Session,
    status_filter: str | None = None,
) -> list[competitions_models.Competition]:
    stmt = select(competitions_models.Competition).where(competitions_models.Competition.user_id == user_id)
    if status_filter:
        stmt = stmt.where(competitions_models.Competition.status == status_filter)
    stmt = stmt.order_by(competitions_models.Competition.competition_date.desc())
    return list(db.scalars(stmt).all())


@core_decorators.handle_db_errors
def get_competition(user_id: int, competition_id: int, db: Session) -> competitions_models.Competition:
    stmt = select(competitions_models.Competition).where(
        competitions_models.Competition.id == competition_id,
        competitions_models.Competition.user_id == user_id,
    )
    row = db.scalars(stmt).first()
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Competition not found")
    return row


@core_decorators.handle_db_errors
def get_next_competition(
    user_id: int, db: Session, today: date | None = None
) -> competitions_models.Competition | None:
    """The earliest still-upcoming race on/after ``today``, or ``None``."""
    today = today or date.today()
    stmt = (
        select(competitions_models.Competition)
        .where(
            competitions_models.Competition.user_id == user_id,
            competitions_models.Competition.status == "upcoming",
            competitions_models.Competition.competition_date >= today,
        )
        .order_by(competitions_models.Competition.competition_date.asc())
    )
    return db.scalars(stmt).first()


@core_decorators.handle_db_errors
def create_competition(
    user_id: int,
    payload: competitions_schema.CompetitionCreate,
    db: Session,
) -> competitions_models.Competition:
    row = competitions_models.Competition(user_id=user_id, **payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@core_decorators.handle_db_errors
def update_competition(
    user_id: int,
    competition_id: int,
    payload: competitions_schema.CompetitionUpdate,
    db: Session,
) -> competitions_models.Competition:
    row = get_competition(user_id, competition_id, db)
    for key, value in payload.model_dump().items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row


@core_decorators.handle_db_errors
def delete_competition(user_id: int, competition_id: int, db: Session) -> None:
    row = get_competition(user_id, competition_id, db)
    db.delete(row)
    db.commit()


def readiness_snapshot(
    user_id: int,
    competition: competitions_models.Competition,
    db: Session,
    today: date | None = None,
) -> competitions_schema.NextCompetitionRead:
    """Readiness estimate for the next-race widget (best-effort data).

    Uses every logged activity in the trailing 28 days regardless of sport —
    the same assumption the offline client makes, so numbers stay comparable.
    With no data at all the estimate is simply 0, never an error.
    """
    today = today or date.today()
    window_start = today - timedelta(days=_TRACKING_WINDOW_DAYS - 1)
    rows = db.scalars(
        select(activities_models.Activity.distance).where(
            activities_models.Activity.user_id == user_id,
            func.date(activities_models.Activity.start_time) >= window_start.isoformat(),
        )
    ).all()
    total_meters = sum(int(d or 0) for d in rows)
    avg_weekly_km = total_meters / 1000 / _WEEKS_IN_WINDOW
    required = float(_required_weekly_km(competition.distance_km))
    days_left = max((competition.competition_date - today).days, 0)
    return competitions_schema.NextCompetitionRead(
        competition=competitions_schema.CompetitionRead.model_validate(competition),
        days_left=days_left,
        avg_weekly_km=round(avg_weekly_km, 2),
        required_weekly_km=required,
        readiness=min(avg_weekly_km / required, 1.0) if required > 0 else 1.0,
    )
