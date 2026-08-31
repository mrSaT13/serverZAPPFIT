"""Add nutrition meal_logs + wger settings.

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-08-31
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: str | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "meal_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("meal_type", sa.String(length=20), nullable=False),
        sa.Column("product_name", sa.String(length=250), nullable=False),
        sa.Column("calories", sa.Float(), nullable=True),
        sa.Column("protein", sa.Float(), nullable=True),
        sa.Column("carbs", sa.Float(), nullable=True),
        sa.Column("fat", sa.Float(), nullable=True),
        sa.Column("portion_g", sa.Float(), nullable=True),
        sa.Column("off_barcode", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_meal_logs_user_id", "meal_logs", ["user_id"])
    op.create_index("ix_meal_logs_date", "meal_logs", ["date"])
    op.create_index("ix_meal_logs_off_barcode", "meal_logs", ["off_barcode"])

    op.create_table(
        "user_nutrition_settings",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("wger_base_url", sa.String(length=500), nullable=True),
        sa.Column("wger_api_key", sa.String(length=512), nullable=True),
        sa.Column("wger_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )


def downgrade() -> None:
    op.drop_table("user_nutrition_settings")
    op.drop_index("ix_meal_logs_off_barcode", table_name="meal_logs")
    op.drop_index("ix_meal_logs_date", table_name="meal_logs")
    op.drop_index("ix_meal_logs_user_id", table_name="meal_logs")
    op.drop_table("meal_logs")
