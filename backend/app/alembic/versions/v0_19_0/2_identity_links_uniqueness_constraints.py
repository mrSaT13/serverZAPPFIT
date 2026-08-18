"""2: identity_links uniqueness constraints

Revision ID: b7f3c9d42a6e
Revises: a1b2c3d4e5f6
Create Date: 2026-06-07 00:00:00.000000

"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b7f3c9d42a6e"
down_revision: str | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Remove duplicate rows before adding unique constraints.
    # For (user_id, idp_id): keep the row with the smallest id.
    op.execute(
        sa.text(
            """
            DELETE FROM users_identity_providers
            WHERE id NOT IN (
                SELECT MIN(id)
                FROM users_identity_providers
                GROUP BY user_id, idp_id
            )
            """
        )
    )
    # For (idp_id, idp_subject): keep the row with the smallest id
    # after the first dedup pass (a row removed above can't create
    # a remaining duplicate here, but we guard for safety).
    op.execute(
        sa.text(
            """
            DELETE FROM users_identity_providers
            WHERE id NOT IN (
                SELECT MIN(id)
                FROM users_identity_providers
                GROUP BY idp_id, idp_subject
            )
            """
        )
    )

    # Add unique constraints.
    op.create_unique_constraint(
        "uq_identity_links_user_idp",
        "users_identity_providers",
        ["user_id", "idp_id"],
    )
    op.create_unique_constraint(
        "uq_identity_links_idp_subject",
        "users_identity_providers",
        ["idp_id", "idp_subject"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_identity_links_idp_subject",
        "users_identity_providers",
        type_="unique",
    )
    op.drop_constraint(
        "uq_identity_links_user_idp",
        "users_identity_providers",
        type_="unique",
    )
