"""Planned workout dates (mobile calendar sync).

``workout_schedule`` — rows pushed by the mobile app's local ``plan_schedule``
table and rendered on the web dashboard calendar. (plan_id, date) is treated
as a natural key on client re-sync (upsert, not append).

Revision ID: d0e1f2a3b4c5
Revises: c9d0e1f2a3b4
Create Date: 2026-11-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d0e1f2a3b4c5"
down_revision: str | None = "c9d0e1f2a3b4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "workout_schedule",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("plan_id", sa.Integer(), sa.ForeignKey("workout_plans.id", ondelete="SET NULL"), nullable=True),
        sa.Column("plan_name", sa.String(length=250), nullable=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("time", sa.String(length=5), nullable=True),
        sa.Column("reminder_minutes", sa.Integer(), nullable=True),
        sa.Column("completed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(op.f("ix_workout_schedule_user_id"), "workout_schedule", ["user_id"])
    op.create_index(op.f("ix_workout_schedule_plan_id"), "workout_schedule", ["plan_id"])
    op.create_index(op.f("ix_workout_schedule_date"), "workout_schedule", ["date"])


def downgrade() -> None:
    op.drop_table("workout_schedule")
