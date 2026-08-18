"""9: ZAPFIT setup wizard and branding fields

Adds the columns that drive the first-time setup wizard and the fork's
rebranding hook:

* ``setup_completed`` — flips to ``True`` once the wizard has been run by
  the first administrator. The public login page reads this flag to decide
  whether to redirect newly-authenticated admins to the wizard.
* ``default_theme`` — default UI theme for new sessions
  (``light``/``dark``/``system``). Mirrors the new
  :class:`ThemePreference` enum.
* ``default_language`` — default BCP 47 language tag for new sessions.
* ``brand_name`` — display brand name rendered in the UI. Stored as a row
  rather than a constant so the fork can be re-themed without a code
  change.

Revision ID: b1c2d3e4f5a6
Revises: a4dd90d4f76e
Create Date: 2026-08-18 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b1c2d3e4f5a6"
down_revision: str | None = "a4dd90d4f76e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add the setup-wizard and branding columns to ``server_settings``."""
    op.add_column(
        "server_settings",
        sa.Column(
            "setup_completed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
            comment=(
                "Whether the first-time setup wizard has been completed. "
                "Drives the post-login wizard redirect on the frontend."
            ),
        ),
    )
    op.add_column(
        "server_settings",
        sa.Column(
            "default_theme",
            sa.String(length=20),
            nullable=False,
            server_default="system",
            comment="Default UI theme for new sessions (light, dark, system)",
        ),
    )
    op.add_column(
        "server_settings",
        sa.Column(
            "default_language",
            sa.String(length=35),
            nullable=False,
            server_default="en",
            comment="Default BCP 47 language tag for new sessions",
        ),
    )
    op.add_column(
        "server_settings",
        sa.Column(
            "brand_name",
            sa.String(length=64),
            nullable=False,
            server_default="ZAPFIT",
            comment="Display brand name shown in the UI (fork rebranding hook)",
        ),
    )


def downgrade() -> None:
    """Drop the setup-wizard and branding columns."""
    op.drop_column("server_settings", "brand_name")
    op.drop_column("server_settings", "default_language")
    op.drop_column("server_settings", "default_theme")
    op.drop_column("server_settings", "setup_completed")
