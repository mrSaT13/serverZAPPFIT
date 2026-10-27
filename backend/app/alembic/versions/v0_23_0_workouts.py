"""Add strength workouts + exercise catalog tables.

Revision ID: b4f2a1c83e20
Revises: a1870b5d1097
Create Date: 2026-10-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b4f2a1c83e20"
down_revision: str | None = "a1870b5d1097"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "exercise_catalog",
        sa.Column("wger_id", sa.Integer(), nullable=False),
        sa.Column("uuid", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=250), nullable=False),
        sa.Column("translations", sa.JSON(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("equipment_ids", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("muscle_ids", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("muscle_ids_secondary", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("variation_group", sa.String(length=50), nullable=True),
        sa.Column("license_author", sa.String(length=250), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("wger_id"),
    )
    op.create_index("ix_exercise_catalog_uuid", "exercise_catalog", ["uuid"], unique=True)
    op.create_index("ix_exercise_catalog_name", "exercise_catalog", ["name"])
    op.create_index("ix_exercise_catalog_category_id", "exercise_catalog", ["category_id"])

    op.create_table(
        "workout_plans",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=250), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=True),
        sa.Column("source", sa.String(length=20), nullable=False, server_default=sa.text("'manual'")),
        sa.Column("wger_plan_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_workout_plans_user_id", "workout_plans", ["user_id"])
    op.create_index("ix_workout_plans_wger_plan_id", "workout_plans", ["wger_plan_id"])

    op.create_table(
        "workout_plan_exercises",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("day_label", sa.String(length=100), nullable=True),
        sa.Column("name", sa.String(length=250), nullable=False),
        sa.Column("muscle_group", sa.String(length=100), nullable=True),
        sa.Column("wger_exercise_id", sa.Integer(), nullable=True),
        sa.Column("notes", sa.String(length=500), nullable=True),
        sa.Column("target_sets", sa.Integer(), nullable=True),
        sa.Column("target_reps", sa.String(length=50), nullable=True),
        sa.Column("target_weight_kg", sa.Float(), nullable=True),
        sa.Column("rest_s", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["plan_id"], ["workout_plans.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_workout_plan_exercises_plan_id", "workout_plan_exercises", ["plan_id"])
    op.create_index("ix_workout_plan_exercises_wger_exercise_id", "workout_plan_exercises", ["wger_exercise_id"])

    op.create_table(
        "workout_sessions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("duration_min", sa.Float(), nullable=True),
        sa.Column("calories", sa.Float(), nullable=True),
        sa.Column("comment", sa.String(length=1000), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["plan_id"], ["workout_plans.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_workout_sessions_user_id", "workout_sessions", ["user_id"])
    op.create_index("ix_workout_sessions_plan_id", "workout_sessions", ["plan_id"])
    op.create_index("ix_workout_sessions_date", "workout_sessions", ["date"])

    op.create_table(
        "workout_sets",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("exercise_name", sa.String(length=250), nullable=False),
        sa.Column("wger_exercise_id", sa.Integer(), nullable=True),
        sa.Column("set_no", sa.Integer(), nullable=False),
        sa.Column("weight_kg", sa.Float(), nullable=True),
        sa.Column("reps", sa.Integer(), nullable=True),
        sa.Column("rpe", sa.Float(), nullable=True),
        sa.Column("completed", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.ForeignKeyConstraint(["session_id"], ["workout_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_workout_sets_session_id", "workout_sets", ["session_id"])
    op.create_index("ix_workout_sets_exercise_name", "workout_sets", ["exercise_name"])


def downgrade() -> None:
    op.drop_table("workout_sets")
    op.drop_table("workout_sessions")
    op.drop_table("workout_plan_exercises")
    op.drop_table("workout_plans")
    op.drop_index("ix_exercise_catalog_category_id", table_name="exercise_catalog")
    op.drop_index("ix_exercise_catalog_name", table_name="exercise_catalog")
    op.drop_index("ix_exercise_catalog_uuid", table_name="exercise_catalog")
    op.drop_table("exercise_catalog")
