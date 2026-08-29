"""Add SMTP settings to server_settings for admin UI.

Revision ID: c9d1e2f3a4b5
Revises: b1c2d3e4f5a6
Create Date: 2026-08-29 00:00:00.000000

Adds columns to ``server_settings`` so SMTP can be configured via the
admin UI instead of only env vars:
- smtp_host, smtp_port, smtp_username, smtp_password (encrypted), smtp_from,
  smtp_secure, smtp_secure_type
The backend ``AppriseService`` prefers DB values when ``smtp_host`` is set,
otherwise falls back to env (SMTP_HOST etc.). Password is stored Fernet-encrypted
like ``tileserver_api_key``.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c9d1e2f3a4b5"
down_revision: str | None = "b1c2d3e4f5a6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("server_settings", sa.Column("smtp_host", sa.String(length=255), nullable=True, comment="SMTP host for transactional email (overrides SMTP_HOST env)"))
    op.add_column("server_settings", sa.Column("smtp_port", sa.Integer(), nullable=True, comment="SMTP port (overrides SMTP_PORT env)"))
    op.add_column("server_settings", sa.Column("smtp_username", sa.String(length=320), nullable=True, comment="SMTP username (overrides SMTP_USERNAME env)"))
    op.add_column("server_settings", sa.Column("smtp_password", sa.String(length=512), nullable=True, comment="SMTP password encrypted with Fernet (overrides SMTP_PASSWORD env)"))
    op.add_column("server_settings", sa.Column("smtp_from", sa.String(length=320), nullable=True, comment="SMTP From address (overrides SMTP_FROM env)"))
    op.add_column("server_settings", sa.Column("smtp_secure", sa.Boolean(), nullable=True, comment="Use secure SMTP (overrides SMTP_SECURE env)"))
    op.add_column("server_settings", sa.Column("smtp_secure_type", sa.String(length=10), nullable=True, comment="Secure type: starttls or ssl (overrides SMTP_SECURE_TYPE env)"))


def downgrade() -> None:
    op.drop_column("server_settings", "smtp_secure_type")
    op.drop_column("server_settings", "smtp_secure")
    op.drop_column("server_settings", "smtp_from")
    op.drop_column("server_settings", "smtp_password")
    op.drop_column("server_settings", "smtp_username")
    op.drop_column("server_settings", "smtp_port")
    op.drop_column("server_settings", "smtp_host")
