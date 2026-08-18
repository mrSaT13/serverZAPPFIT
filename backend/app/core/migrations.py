"""Migration consistency checks run during backend startup."""

import core.logger as core_logger
import migrations.utils as migrations_utils
from core.database import SessionLocal


async def check_migrations() -> None:
    """
    Check for pending custom migration records.

    Args:
        None.

    Returns:
        None.

    Raises:
        Exception: Propagates migration check failures.
    """
    core_logger.print_to_log_and_console("Checking for migrations not executed")

    with SessionLocal() as db:
        await migrations_utils.check_migrations_not_executed(db)

    core_logger.print_to_log_and_console("Migration check completed")
