"""3: add users_local_credentials table, backfill, drop users.password

Revision ID: c8e1f0a2b3d4
Revises: b7f3c9d42a6e
Create Date: 2026-06-08 00:00:00.000000

Credential-table split. Creates the auth-owned ``users_local_credentials``
table, backfills one row for every user that currently has a non-empty
``users.password`` hash (behavior-preserving — existing hashes, including the
random hashes generated for SSO-only accounts, are copied verbatim), and then
drops the legacy ``users.password`` column. The credential table becomes the
sole source of truth for local password hashes.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c8e1f0a2b3d4"
down_revision: str | None = "b7f3c9d42a6e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create users_local_credentials, backfill, and drop users.password."""
    op.create_table(
        "users_local_credentials",
        sa.Column(
            "user_id",
            sa.Integer(),
            nullable=False,
            comment="FK to users — one row per user with a local password",
        ),
        sa.Column(
            "password_hash",
            sa.String(250),
            nullable=False,
            comment="Local account password hash",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("user_id"),
    )

    # Behavior-preserving backfill: copy every non-empty password hash into
    # the new table. SSO-only accounts whose password is NULL or empty get no
    # row, which makes "has a local password" a simple row-existence check.
    op.execute(
        sa.text(
            """
            INSERT INTO users_local_credentials (user_id, password_hash, created_at, updated_at)
            SELECT id, password, now(), now()
            FROM users
            WHERE password IS NOT NULL AND password <> ''
            """
        )
    )

    # Drop the legacy column now that the data lives in the credential table.
    op.drop_column("users", "password")


def downgrade() -> None:
    """Re-add users.password, restore hashes, and drop the credential table."""
    # Re-add the column as nullable so existing rows can be backfilled before
    # the NOT NULL constraint is restored.
    op.add_column(
        "users",
        sa.Column(
            "password",
            sa.String(250),
            nullable=True,
            comment="User password (hash) — restored by downgrade",
        ),
    )

    # Restore hashes from the credential table.
    op.execute(
        sa.text(
            """
            UPDATE users
            SET password = ulc.password_hash
            FROM users_local_credentials AS ulc
            WHERE users.id = ulc.user_id
            """
        )
    )

    # Users without a credential row (SSO-only / empty before the split) get
    # the original empty-string sentinel so the NOT NULL constraint holds.
    op.execute(sa.text("UPDATE users SET password = '' WHERE password IS NULL"))

    op.alter_column("users", "password", nullable=False)

    op.execute(sa.text("DELETE FROM users_local_credentials"))
    op.drop_table("users_local_credentials")
