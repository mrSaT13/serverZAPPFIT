"""7: migrate preferred_language to BCP 47 language tags

Aligns ``users.preferred_language`` with the IETF BCP 47 language tags used by
the frontend. The legacy ad-hoc codes are converted: ``us`` -> ``en``,
``cn`` -> ``zh-Hans``, ``tw`` -> ``zh-Hant`` and ``pt`` -> ``pt-PT``. Every
other stored code was already a valid BCP 47 language subtag and is left
unchanged.

The column is also widened from ``VARCHAR(5)`` to ``VARCHAR(35)`` because the
new script-tagged values (e.g. ``zh-Hans``) exceed the previous limit, and to
leave headroom for future regional variants (e.g. ``en-GB``).

Revision ID: c4d5e6f7a8b9
Revises: f3a4b5c6d7e8
Create Date: 2026-06-28 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c4d5e6f7a8b9"
down_revision: str | None = "f3a4b5c6d7e8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Legacy backend code -> canonical BCP 47 tag. Only these four differ; the
# remaining codes were already valid BCP 47 language subtags.
_CODE_MAP: tuple[tuple[str, str], ...] = (
    ("us", "en"),
    ("cn", "zh-Hans"),
    ("tw", "zh-Hant"),
    ("pt", "pt-PT"),
)

_OLD_COMMENT = "User preferred language (en, pt, others)"
_NEW_COMMENT = "User preferred BCP 47 language tag (en, pt-PT, zh-Hans, others)"


def upgrade() -> None:
    """Widen the column, then convert legacy codes to BCP 47 tags."""
    # Widen first so the longer script-tagged values (e.g. ``zh-Hans``) fit.
    op.alter_column(
        "users",
        "preferred_language",
        existing_type=sa.String(length=5),
        type_=sa.String(length=35),
        existing_nullable=False,
        existing_comment=_OLD_COMMENT,
        comment=_NEW_COMMENT,
    )
    for legacy, canonical in _CODE_MAP:
        op.execute(
            sa.text("UPDATE users SET preferred_language = :new WHERE preferred_language = :old").bindparams(
                new=canonical, old=legacy
            )
        )


def downgrade() -> None:
    """Restore the legacy codes, then shrink the column back to VARCHAR(5)."""
    # Revert values first: the legacy codes fit within the narrower column.
    for legacy, canonical in _CODE_MAP:
        op.execute(
            sa.text("UPDATE users SET preferred_language = :old WHERE preferred_language = :new").bindparams(
                new=canonical, old=legacy
            )
        )
    op.alter_column(
        "users",
        "preferred_language",
        existing_type=sa.String(length=35),
        type_=sa.String(length=5),
        existing_nullable=False,
        existing_comment=_NEW_COMMENT,
        comment=_OLD_COMMENT,
    )
