"""User UI appearance preferences (theme + accent color).

``users.theme`` / ``users.accent_color`` — the web dashboard's appearance
choice synced to the profile so it follows the user across browsers and
devices (previously localStorage-only). Server never validates the accent
preset id (unknown ids fall back to blue client-side) — only the length is
constrained; theme is constrained to light/dark/system by CHECK.

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
Create Date: 2026-10-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c9d0e1f2a3b4"
down_revision: str | None = "b8c9d0e1f2a3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("theme", sa.String(length=20), nullable=False, server_default="system"))
    op.add_column("users", sa.Column("accent_color", sa.String(length=20), nullable=False, server_default="blue"))


def downgrade() -> None:
    op.drop_column("users", "accent_color")
    op.drop_column("users", "theme")
