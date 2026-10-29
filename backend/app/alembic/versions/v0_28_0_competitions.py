"""User competitions (races) with training-readiness surfacing.

``competitions`` — the synced source of truth for the mobile client's local
Preparation tab (name, race day, distance, results once raced). The web
"Обзор" dashboard reads the next upcoming race through
``GET /api/v1/competitions/next`` and shows a training-readiness estimate
computed from logged activities.

Revision ID: b8c9d0e1f2a3
Revises: a7b2c3d4e5f6
Create Date: 2026-10-29
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b8c9d0e1f2a3"
down_revision: str | None = "a7b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "competitions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("competition_date", sa.Date(), nullable=False),
        sa.Column("distance_km", sa.Float(), nullable=False),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default=sa.text("'upcoming'")),
        sa.Column("place", sa.Integer(), nullable=True),
        sa.Column("total_participants", sa.Integer(), nullable=True),
        sa.Column("result_time_s", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_competitions_user_id", "competitions", ["user_id"])
    op.create_index("ix_competitions_competition_date", "competitions", ["competition_date"])


def downgrade() -> None:
    op.drop_index("ix_competitions_competition_date", table_name="competitions")
    op.drop_index("ix_competitions_user_id", table_name="competitions")
    op.drop_table("competitions")
