"""1: move MFA columns to separate users_mfa table

Revision ID: a1b2c3d4e5f6
Revises: 895a29b12c8c
Create Date: 2026-05-27 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "895a29b12c8c"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create users_mfa and backfill from users."""
    op.create_table(
        "users_mfa",
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            nullable=False,
            comment="FK to users — one row per user",
        ),
        sa.Column(
            "mfa_enabled",
            sa.Boolean(),
            nullable=False,
            comment="Whether TOTP MFA is active for this user",
        ),
        sa.Column(
            "mfa_secret",
            sa.String(512),
            nullable=True,
            comment="Fernet-encrypted TOTP secret",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            name="uq_users_mfa_user_id",
        ),
    )
    op.create_index(
        "ix_users_mfa_user_id",
        "users_mfa",
        ["user_id"],
        unique=False,
    )

    # Backfill: one row per existing user, copying the MFA
    # columns from the ``users`` table.  Only users that have
    # ``mfa_enabled = true`` carry a non-NULL ``mfa_secret``,
    # but we create a row for every user so that future writes
    # can do a simple UPDATE rather than an INSERT-OR-UPDATE.
    op.execute(
        sa.text(
            """
            INSERT INTO users_mfa (user_id, mfa_enabled, mfa_secret)
            SELECT id, mfa_enabled, mfa_secret
            FROM users
            """
        )
    )
    """Drop mfa_enabled and mfa_secret columns from users."""
    op.drop_column("users", "mfa_secret")
    op.drop_column("users", "mfa_enabled")


def downgrade() -> None:
    """Re-add legacy MFA columns and copy data from users_mfa."""
    op.add_column(
        "users",
        sa.Column(
            "mfa_secret",
            sa.String(512),
            nullable=True,
            comment=("User MFA secret for TOTP generation (encrypted at rest) — restored by downgrade"),
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "mfa_enabled",
            sa.Boolean(),
            nullable=True,
            comment=("Whether MFA is enabled — restored by downgrade"),
        ),
    )
    op.execute(
        sa.text(
            """
            UPDATE users
            SET mfa_enabled = um.mfa_enabled,
                mfa_secret  = um.mfa_secret
            FROM users_mfa AS um
            WHERE users.id = um.user_id
            """
        )
    )
    op.drop_index(
        "ix_users_mfa_user_id",
        table_name="users_mfa",
    )
    op.drop_table("users_mfa")
