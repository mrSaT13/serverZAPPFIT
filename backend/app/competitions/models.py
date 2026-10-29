"""User competitions (races) with training-readiness surfacing.

Server-side counterpart of the mobile client's local Preparation tab: the
client tracks competitions locally (JSON in preferences), this table is the
synced source of truth — records survive device changes and the web
"Обзор" dashboard can surface the next race with a training-readiness
estimate computed from logged activities.

Lifecycle: a row starts ``upcoming``; once raced, the client/user completes
it by sending the results (``status="completed"`` plus ``place`` /
``total_participants`` / ``result_time_s``), and past races act as history.
"""

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class Competition(Base):
    __tablename__ = "competitions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Display name, e.g. "Марафон "Белые ночи"" / "City Half".
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    # Race day (no time zone games — a date is all the countdown needs).
    competition_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    # Declared race distance in kilometres (5, 10, 21.0975 …).
    distance_km: Mapped[float] = mapped_column(Float, nullable=False)
    # Free-form note (place, pace goal, gear checklist …), client-provided.
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # "upcoming" until raced, "completed" once results are recorded.
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="upcoming", server_default="upcoming")
    # Race results (filled on completion; blank while upcoming).
    place: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_participants: Mapped[int | None] = mapped_column(Integer, nullable=True)
    result_time_s: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
