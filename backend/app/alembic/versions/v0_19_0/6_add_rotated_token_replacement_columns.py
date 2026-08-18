"""6: add replacement-token columns to rotated_refresh_tokens

Adds two nullable columns used by the idempotent in-grace refresh replay:
``replacement_refresh_token`` stores the Fernet-encrypted refresh token minted
when the row's token was rotated out, and ``replacement_refresh_token_exp``
stores that replacement's expiry. They let a legitimate retry presenting an
already-rotated token (a lost rotation response or a racing/duplicate refresh)
be replayed with the original replacement instead of being rejected with a 401.

Both columns are nullable, so existing rows are unaffected and no backfill is
required; this is a pure schema change.

Revision ID: f3a4b5c6d7e8
Revises: e7d8c9b0a1f2
Create Date: 2026-06-28 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f3a4b5c6d7e8"
down_revision: str | None = "e7d8c9b0a1f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add the replacement-token columns to rotated_refresh_tokens."""
    op.add_column(
        "rotated_refresh_tokens",
        sa.Column(
            "replacement_refresh_token",
            sa.Text(),
            nullable=True,
            comment="Fernet-encrypted replacement refresh token for idempotent in-grace replay",
        ),
    )
    op.add_column(
        "rotated_refresh_tokens",
        sa.Column(
            "replacement_refresh_token_exp",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Expiry of the replacement refresh token",
        ),
    )


def downgrade() -> None:
    """Drop the replacement-token columns from rotated_refresh_tokens."""
    op.drop_column("rotated_refresh_tokens", "replacement_refresh_token_exp")
    op.drop_column("rotated_refresh_tokens", "replacement_refresh_token")
