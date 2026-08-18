"""4: add zone_percentages column to activities_streams

Revision ID: b2c3d4e5f6a7
Revises: c8e1f0a2b3d4
Create Date: 2026-06-11 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: str | None = "c8e1f0a2b3d4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add the nullable zone_percentages JSON column."""
    op.add_column(
        "activities_streams",
        sa.Column(
            "zone_percentages",
            sa.JSON(),
            nullable=True,
            comment="Pre-computed zone breakdowns keyed by metric (e.g. 'hr', 'power')",
        ),
    )
    op.execute(
        """
    INSERT INTO migrations (id, name, description, executed) VALUES
    (7, 'v0.19.0', 'Backfill pre-computed HR zone_percentages for existing streams', false);
    """
    )


def downgrade() -> None:
    """Drop the zone_percentages column and remove the migration registration."""
    op.execute("DELETE FROM migrations WHERE id = 7;")
    op.drop_column("activities_streams", "zone_percentages")
