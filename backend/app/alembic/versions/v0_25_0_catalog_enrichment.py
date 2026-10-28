"""Enrich exercise catalog with wger aliases, tips and license names.

Revision ID: e5f6a7b8c9d0
Revises: d7e9f2a4c618
Create Date: 2026-10-28
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e5f6a7b8c9d0"
down_revision: str | None = "d7e9f2a4c618"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "exercise_catalog",
        sa.Column("aliases", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
    )
    op.add_column(
        "exercise_catalog",
        sa.Column("tips", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
    )
    op.add_column(
        "exercise_catalog",
        sa.Column("license_name", sa.String(length=100), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("exercise_catalog", "license_name")
    op.drop_column("exercise_catalog", "tips")
    op.drop_column("exercise_catalog", "aliases")
