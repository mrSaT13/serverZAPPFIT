"""v0.19.0 ZAPFIT fitness metrics

Revision ID: a1b2c3d4e5f6
Revises: b1c2d3e4f5a6
Create Date: 2026-08-19 12:00:00.000000

"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "b1c2d3e4f5a6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add ZAPFIT fitness metrics columns to activities table
    op.add_column(
        "activities",
        sa.Column(
            "vo2max",
            sa.Numeric(precision=5, scale=2),
            nullable=True,
            comment="Estimated VO2max (ml/kg/min)",
        ),
    )
    op.add_column(
        "activities",
        sa.Column(
            "tss",
            sa.Integer(),
            nullable=True,
            comment="Training Stress Score",
        ),
    )
    op.add_column(
        "activities",
        sa.Column(
            "hr_tss",
            sa.Integer(),
            nullable=True,
            comment="Heart Rate Training Stress Score",
        ),
    )
    op.add_column(
        "activities",
        sa.Column(
            "trimp",
            sa.Integer(),
            nullable=True,
            comment="TRIMP (Banister exponential)",
        ),
    )
    op.add_column(
        "activities",
        sa.Column(
            "intensity_factor",
            sa.Numeric(precision=5, scale=3),
            nullable=True,
            comment="Intensity Factor (0.000-1.500)",
        ),
    )
    op.add_column(
        "activities",
        sa.Column(
            "aerobic_te",
            sa.Numeric(precision=3, scale=1),
            nullable=True,
            comment="Aerobic Training Effect (1.0-5.0)",
        ),
    )
    op.add_column(
        "activities",
        sa.Column(
            "anaerobic_te",
            sa.Numeric(precision=3, scale=1),
            nullable=True,
            comment="Anaerobic Training Effect (1.0-5.0)",
        ),
    )
    op.add_column(
        "activities",
        sa.Column(
            "epoc",
            sa.Numeric(precision=8, scale=2),
            nullable=True,
            comment="EPOC in kcal",
        ),
    )
    op.add_column(
        "activities",
        sa.Column(
            "suffer_score",
            sa.Integer(),
            nullable=True,
            comment="Suffer Score (0-100)",
        ),
    )
    op.add_column(
        "activities",
        sa.Column(
            "efficiency_factor",
            sa.Numeric(precision=8, scale=4),
            nullable=True,
            comment="Efficiency Factor (pace per HR)",
        ),
    )


def downgrade() -> None:
    op.drop_column("activities", "efficiency_factor")
    op.drop_column("activities", "suffer_score")
    op.drop_column("activities", "epoc")
    op.drop_column("activities", "anaerobic_te")
    op.drop_column("activities", "aerobic_te")
    op.drop_column("activities", "intensity_factor")
    op.drop_column("activities", "trimp")
    op.drop_column("activities", "hr_tss")
    op.drop_column("activities", "tss")
    op.drop_column("activities", "vo2max")
