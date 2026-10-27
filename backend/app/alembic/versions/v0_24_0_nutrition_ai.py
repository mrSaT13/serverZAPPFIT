"""Add AI nutrition assistant server settings.

Revision ID: d7e9f2a4c618
Revises: b4f2a1c83e20
Create Date: 2026-10-27
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d7e9f2a4c618"
down_revision: str | None = "b4f2a1c83e20"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "server_settings",
        sa.Column("ai_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column(
        "server_settings",
        sa.Column("ai_base_url", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "server_settings",
        sa.Column("ai_model", sa.String(length=100), nullable=True),
    )
    op.add_column(
        "server_settings",
        sa.Column("ai_api_key", sa.String(length=512), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("server_settings", "ai_api_key")
    op.drop_column("server_settings", "ai_model")
    op.drop_column("server_settings", "ai_base_url")
    op.drop_column("server_settings", "ai_enabled")
