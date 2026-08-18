"""5: repair health_sleep integer columns left as numeric by the v0.16.0 pre-release

The original v0.16.0 health_sleep migration created several integer metrics as
DECIMAL(10, 2). That was corrected to Integer for new installs in commit
09538580 before the stable v0.16.0 release, but databases that had already run
the migration during a v0.16.0 pre-release keep the numeric columns: Alembic
does not re-run an applied revision and no later migration repairs the types.
The read schema declares these fields as StrictInt, so any Decimal value coming
from Garmin (respiration, stress, etc.) breaks serialization and the
/health/sleep endpoint returns 500.

This migration converts those columns back to Integer, but only when they are
still numeric, so it is a no-op on installs that already have the correct type.

Revision ID: e7d8c9b0a1f2
Revises: b2c3d4e5f6a7
Create Date: 2026-06-21 00:00:00.000000

"""

from collections.abc import Sequence

from alembic import op

revision: str = "e7d8c9b0a1f2"
down_revision: str | None = "b2c3d4e5f6a7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Convert the affected columns from numeric to integer when still numeric.

    The column list below is the set the v0.16.0 pre-release migration created as
    DECIMAL(10, 2) and that commit 09538580 later defined as Integer for fresh
    installs.
    """
    op.execute(
        """
        DO $$
        DECLARE
            col text;
            cols text[] := ARRAY[
                'avg_heart_rate', 'avg_spo2', 'avg_respiration',
                'lowest_respiration', 'highest_respiration',
                'avg_stress_level', 'avg_sleep_stress'
            ];
        BEGIN
            FOREACH col IN ARRAY cols LOOP
                IF EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_schema = current_schema()
                      AND table_name = 'health_sleep'
                      AND column_name = col
                      AND data_type = 'numeric'
                ) THEN
                    EXECUTE format(
                        'ALTER TABLE health_sleep ALTER COLUMN %I TYPE integer USING round(%I)::integer',
                        col, col
                    );
                END IF;
            END LOOP;
        END $$;
        """
    )


def downgrade() -> None:
    """Restore the affected columns to numeric(10, 2) when currently integer."""
    op.execute(
        """
        DO $$
        DECLARE
            col text;
            cols text[] := ARRAY[
                'avg_heart_rate', 'avg_spo2', 'avg_respiration',
                'lowest_respiration', 'highest_respiration',
                'avg_stress_level', 'avg_sleep_stress'
            ];
        BEGIN
            FOREACH col IN ARRAY cols LOOP
                IF EXISTS (
                    SELECT 1 FROM information_schema.columns
                    WHERE table_schema = current_schema()
                      AND table_name = 'health_sleep'
                      AND column_name = col
                      AND data_type = 'integer'
                ) THEN
                    EXECUTE format(
                        'ALTER TABLE health_sleep ALTER COLUMN %I TYPE numeric(10, 2) USING %I::numeric(10, 2)',
                        col, col
                    );
                END IF;
            END LOOP;
        END $$;
        """
    )
