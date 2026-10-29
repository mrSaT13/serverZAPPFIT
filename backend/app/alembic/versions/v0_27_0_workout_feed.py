"""Publish strength sessions to the feed + user training inventory.

- ``users_privacy_settings.publish_workouts_in_feed`` — global opt-in that
  makes every newly logged workout session appear in the activity feed as a
  Strength training activity (type 19).
- ``workout_sessions.activity_id`` — links the session to the activity it
  published so deleting the session removes the feed entry (and a feed-side
  delete just clears the link).
- ``user_equipment`` — the user's own training inventory (dumbbells,
  barbells, kettlebells …) with weights/quantities; the AI planner receives
  it so it only proposes exercises the user can actually perform.

Revision ID: a7b2c3d4e5f6
Revises: e5f6a7b8c9d0
Create Date: 2026-10-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a7b2c3d4e5f6"
down_revision: str | None = "e5f6a7b8c9d0"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users_privacy_settings",
        sa.Column(
            "publish_workouts_in_feed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.add_column(
        "workout_sessions",
        sa.Column("activity_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_workout_sessions_activity_id",
        "workout_sessions",
        "activities",
        ["activity_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_workout_sessions_activity_id", "workout_sessions", ["activity_id"])

    op.create_table(
        "user_equipment",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("equipment_id", sa.Integer(), nullable=True),
        sa.Column("weight_kg", sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_user_equipment_user_id", "user_equipment", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_user_equipment_user_id", table_name="user_equipment")
    op.drop_table("user_equipment")
    op.drop_index("ix_workout_sessions_activity_id", table_name="workout_sessions")
    op.drop_constraint("fk_workout_sessions_activity_id", "workout_sessions", type_="foreignkey")
    op.drop_column("workout_sessions", "activity_id")
    op.drop_column("users_privacy_settings", "publish_workouts_in_feed")
