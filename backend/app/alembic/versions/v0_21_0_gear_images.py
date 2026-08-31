"""Add gear_images table for gear photo carousel.

Revision ID: e8184fe13279
Revises: c9d1e2f3a4b5
Create Date: 2026-08-31
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "e8184fe13279"
down_revision: str | None = "c9d1e2f3a4b5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "gear_images",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("gear_id", sa.Integer(), nullable=False, comment="Gear ID image belongs to"),
        sa.Column("image_path", sa.String(length=500), nullable=False, comment="Filesystem path"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["gear_id"], ["gear.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("image_path"),
    )
    op.create_index("ix_gear_images_gear_id", "gear_images", ["gear_id"])


def downgrade() -> None:
    op.drop_index("ix_gear_images_gear_id", table_name="gear_images")
    op.drop_table("gear_images")
