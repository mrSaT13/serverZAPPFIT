"""Strength-training ORM models: plans, exercises, sessions, set logs.

Design notes:
- Plans hold a list of exercises (position-ordered, optional wger ids after
  import). Sessions are executions of a plan; each set played is stored as a
  row so progress stats (e.g. best set, Epley 1RM) can be queried directly.
- wger is only an import *source*: after import everything lives on this
  server and works offline.
"""

from datetime import date as date_type
from datetime import datetime as datetime_type

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from core.database import Base


class WorkoutPlan(Base):
    __tablename__ = "workout_plans"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(250), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    # 'manual' or 'wger' (imported snapshot; ids kept for provenance only)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="manual")
    wger_plan_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    created_at: Mapped[datetime_type] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime_type] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    exercises: Mapped[list["WorkoutExercise"]] = relationship(
        back_populates="plan",
        cascade="all, delete-orphan",
        order_by="WorkoutExercise.position",
    )


class WorkoutExercise(Base):
    __tablename__ = "workout_plan_exercises"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("workout_plans.id", ondelete="CASCADE"), nullable=False, index=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    # Optional grouping (wger day / user label, e.g. "Legs", "Day 1")
    day_label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    name: Mapped[str] = mapped_column(String(250), nullable=False)
    muscle_group: Mapped[str | None] = mapped_column(String(100), nullable=True)
    wger_exercise_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)
    notes: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Target prescription
    target_sets: Mapped[int | None] = mapped_column(Integer, nullable=True)
    target_reps: Mapped[str | None] = mapped_column(String(50), nullable=True)  # "8-12", "5"
    target_weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    rest_s: Mapped[int | None] = mapped_column(Integer, nullable=True)

    plan: Mapped["WorkoutPlan"] = relationship(back_populates="exercises")


class WorkoutSession(Base):
    __tablename__ = "workout_sessions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_id: Mapped[int | None] = mapped_column(
        ForeignKey("workout_plans.id", ondelete="SET NULL"), nullable=True, index=True
    )
    date: Mapped[date_type] = mapped_column(Date, nullable=False, index=True)
    duration_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    calories: Mapped[float | None] = mapped_column(Float, nullable=True)
    comment: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    # Feed activity published for this session (users with
    # publish_workouts_in_feed enabled); cleared when the activity is deleted.
    activity_id: Mapped[int | None] = mapped_column(
        ForeignKey("activities.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime_type] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    sets: Mapped[list["WorkoutSetLog"]] = relationship(
        back_populates="session", cascade="all, delete-orphan", order_by="WorkoutSetLog.id"
    )


class WorkoutSetLog(Base):
    __tablename__ = "workout_sets"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("workout_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    exercise_name: Mapped[str] = mapped_column(String(250), nullable=False, index=True)
    wger_exercise_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    set_no: Mapped[int] = mapped_column(Integer, nullable=False)
    weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    reps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rpe: Mapped[float | None] = mapped_column(Float, nullable=True)
    completed: Mapped[bool] = mapped_column(default=True, nullable=False)

    session: Mapped["WorkoutSession"] = relationship(back_populates="sets")
