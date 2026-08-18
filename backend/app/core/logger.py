"""Core logging setup for the application.

Provides:
  - JsonFormatter: structured JSON output for production.
  - _DevFormatter: human-readable text for development.
  - RequestIdFilter: injects the current request ID into
    every log record so all logs from a single request
    can be correlated.
  - _build_handler: environment-aware handler factory
    (stdout JSON always in production/demo; file when
    LOGS_DIR is set; file-only in development).
  - setup_main_logger: configures the main, Alembic, and
    APScheduler loggers.
  - Utility helpers for application-level log routing.
"""

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

# NOTE: ``core.config`` is intentionally NOT imported at module top level.
# ``core.config`` depends on this module to emit warnings from its settings
# validators (e.g. invalid SMTP_SECURE_TYPE, memory-backed rate limiting in
# production). A top-level import here would create a circular import that
# only fails when the entry point imports ``core.logger`` before
# ``core.config`` -- the partially-initialized ``core.logger`` module would
# not yet expose ``print_to_log_and_console`` when a validator calls it.
# ``logger`` is the lower-level module: it must not depend on ``config`` at
# import time. The two functions below that genuinely need ``settings``
# import it locally, after both modules have finished initializing.
import core.middleware_request_id as core_middleware_request_id


class RequestIdFilter(logging.Filter):
    """
    Inject the current request ID into every log record.

    Reads the value from
    :func:`core_middleware_request_id.get_request_id`
    and stores it as ``record.request_id`` so formatters
    can reference ``%(request_id)s``.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """
        Add ``request_id`` attribute to the log record.

        Args:
            record: The log record to augment.

        Returns:
            Always True so the record is never suppressed.
        """
        record.request_id = (  # type: ignore[attr-defined]
            core_middleware_request_id.get_request_id()
        )
        return True


# Attributes always present on a LogRecord — excluded from the extra
# context dict so we only surface caller-supplied fields.
_STDLIB_RECORD_ATTRS: frozenset[str] = frozenset(
    (
        "name",
        "msg",
        "args",
        "levelname",
        "levelno",
        "pathname",
        "filename",
        "module",
        "exc_info",
        "exc_text",
        "stack_info",
        "lineno",
        "funcName",
        "created",
        "msecs",
        "relativeCreated",
        "thread",
        "threadName",
        "processName",
        "process",
        "message",
        "taskName",
        "request_id",
        "asctime",
    )
)


class JsonFormatter(logging.Formatter):
    """
    Format log records as newline-delimited JSON.

    Suitable for collection by container orchestrators
    (Docker, Kubernetes) and log aggregation pipelines.
    Each record becomes one JSON object on a single line.
    Any extra fields supplied via ``extra={}`` are emitted
    under a ``context`` key.
    """

    def format(self, record: logging.LogRecord) -> str:
        """
        Serialise a log record to a JSON string.

        Args:
            record: The log record to format.

        Returns:
            Single-line JSON string representing the record.
        """
        entry: dict = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        rid = getattr(record, "request_id", "")
        if rid:
            entry["request_id"] = rid
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        context = {k: v for k, v in record.__dict__.items() if k not in _STDLIB_RECORD_ATTRS}
        if context:
            entry["context"] = context
        return json.dumps(entry, default=str)


class _DevFormatter(logging.Formatter):
    """
    Human-readable formatter for development log files.

    Appends any caller-supplied ``extra`` fields as a
    space-separated ``key=value`` string after the message
    so engineers can see structured context at a glance.
    """

    _BASE = "%(asctime)s - %(name)s - %(levelname)s - [%(request_id)s] - %(message)s"

    def __init__(self) -> None:
        super().__init__(self._BASE)

    def format(self, record: logging.LogRecord) -> str:
        """
        Format the record with extra context appended.

        Args:
            record: The log record to format.

        Returns:
            Formatted string with optional context suffix.
        """
        base = super().format(record)
        context = {k: v for k, v in record.__dict__.items() if k not in _STDLIB_RECORD_ATTRS}
        if not context:
            return base
        ctx_str = " ".join(f"{k}={v!r}" for k, v in context.items())
        return f"{base} | {ctx_str}"


def _build_handler(log_level: int) -> list[logging.Handler]:
    """
    Build the appropriate log handlers for the environment.

    Production always emits JSON to stdout so container
    orchestrators can collect structured logs without file
    mounts. If ``LOGS_DIR`` is configured, a ``FileHandler``
    writing JSON to ``{LOGS_DIR}/app.log`` is also added so
    Docker volume mounts continue to receive log output.
    Development writes human-readable text to
    ``{LOGS_DIR}/app.log`` only.

    Args:
        log_level: Python logging level constant.

    Returns:
        List of configured :class:`logging.Handler` instances.
    """
    # Local import: see top-of-module note. ``setup_main_logger`` /
    # ``_build_handler`` run at app startup, never at import time, so by the
    # time we get here ``core.config`` is fully initialized.
    import core.config as core_config

    def _configure(handler: logging.Handler, formatter: logging.Formatter) -> logging.Handler:
        handler.setFormatter(formatter)
        handler.setLevel(log_level)
        handler.addFilter(RequestIdFilter())
        return handler

    # Treat both "production" and "demo" as deployed
    # environments where stdout JSON is preferred.
    is_deployed = core_config.settings.ENVIRONMENT in ("production", "demo")
    if is_deployed:
        handlers: list[logging.Handler] = [_configure(logging.StreamHandler(sys.stdout), JsonFormatter())]
        # Also write to file when LOGS_DIR is configured so that Docker
        # volume mounts (e.g. /app/backend/logs) continue to receive log
        # output regardless of the ENVIRONMENT value.
        if core_config.settings.LOGS_DIR:
            log_path = f"{core_config.settings.LOGS_DIR}/app.log"
            handlers.append(_configure(logging.FileHandler(log_path), JsonFormatter()))
    else:
        log_path = f"{core_config.settings.LOGS_DIR}/app.log"
        handlers = [_configure(logging.FileHandler(log_path), _DevFormatter())]

    return handlers


def _replace_handlers(
    loggers: tuple[logging.Logger, ...],
    handlers: list[logging.Handler],
) -> None:
    """
    Replace handlers on a set of related loggers.

    Args:
        loggers: Loggers that should share the given handlers.
        handlers: Handlers to attach to every logger.

    Returns:
        None.

    Raises:
        None.
    """
    old_handlers: set[logging.Handler] = set()
    for logger in loggers:
        old_handlers.update(logger.handlers)
        for old_handler in list(logger.handlers):
            logger.removeHandler(old_handler)
        for handler in handlers:
            logger.addHandler(handler)
        logger.propagate = False

    for old_handler in old_handlers:
        old_handler.close()


def setup_main_logger():
    """
    Set up the main application logger.

    Selects a handler appropriate for the current
    environment (JSON stdout in production, plain-text
    file in development). Attaches the same handler to
    the Alembic and APScheduler loggers so their output
    is captured consistently.

    Returns:
        logging.Logger: The configured main logger instance.
    """
    # Local import: see top-of-module note. Deferring this keeps
    # ``core.logger`` free of any import-time dependency on ``core.config``.
    import core.config as core_config

    # Map string log levels to Python logging constants
    log_level_map = {
        "critical": logging.CRITICAL,
        "error": logging.ERROR,
        "warning": logging.WARNING,
        "info": logging.INFO,
        "debug": logging.DEBUG,
        "trace": logging.DEBUG,  # Trace to debug (Python doesn't have trace)
    }

    # Get log level from config, default to WARNING if invalid
    log_level = log_level_map.get(
        core_config.settings.LOG_LEVEL.lower(),
        logging.WARNING,
    )

    main_logger = logging.getLogger("main_logger")
    alembic_logger = logging.getLogger("alembic")
    scheduler_logger = logging.getLogger("apscheduler")
    # Structured upload-audit events emitted by safeuploads.
    # Attaching it here ensures correlation IDs and validation
    # outcomes flow through the same handler/format pipeline
    # as the rest of the backend logs.
    safeuploads_audit_logger = logging.getLogger("safeuploads.audit")

    for logger in (
        main_logger,
        alembic_logger,
        scheduler_logger,
        safeuploads_audit_logger,
    ):
        logger.setLevel(log_level)

    handlers = _build_handler(log_level)
    _replace_handlers(
        (
            main_logger,
            alembic_logger,
            scheduler_logger,
            safeuploads_audit_logger,
        ),
        handlers,
    )
    safeuploads_audit_logger.propagate = True

    return main_logger


def get_main_logger():
    """
    Returns the main logger instance for the application.

    This function retrieves a logger named "main_logger" using Python's
    standard logging module.
    It can be used throughout the application to log messages under a
    consistent logger name.

    Returns:
        logging.Logger: The logger instance named "main_logger".
    """
    return logging.getLogger("main_logger")


def print_to_log(
    message: str,
    log_level: str = "info",
    exc: Exception | None = None,
    context: dict[str, Any] | None = None,
) -> None:
    """
    Logs a message at the specified log level using the main logger.

    Args:
        message (str): The message to log.
        log_level (str, optional): The log level to use ('info', 'error',
            'warning', 'debug'). Defaults to "info".
        exc (Exception, optional): An exception instance to include in the log
            if log_level is "error". Defaults to None.

    Notes:
        - If log_level is "error" and exc is provided, exception information
            will be included in the log.
    """
    main_logger = get_main_logger()
    if log_level == "info":
        main_logger.info(message)
    elif log_level == "error":
        main_logger.error(message, exc_info=exc is not None)
    elif log_level == "warning":
        main_logger.warning(message)
    elif log_level == "debug":
        main_logger.debug(message)
    elif log_level == "critical":
        main_logger.critical(message)


def print_to_log_and_console(message: str, log_level: str = "info", exc: Exception | None = None):
    """
    Logs a message to both the main logger and the console.

    This function temporarily adds a console handler to the main logger, logs
    the provided message at the specified log level (optionally including
    exception information), and then removes the console handler to ensure
    subsequent logs are not printed to the console.

    Args:
        message (str): The message to log.
        log_level (str, optional): The logging level to use (e.g., "info",
            "warning", "error"). Defaults to "info".
        exc (Exception, optional): An exception to include in the log entry.
            Defaults to None.
    """
    main_logger = get_main_logger()

    # Create a temporary console handler
    console_handler = logging.StreamHandler()
    console_formatter = logging.Formatter("%(levelname)s:     %(message)s")
    console_handler.setFormatter(console_formatter)

    # Add console handler temporarily
    main_logger.addHandler(console_handler)

    print_to_log(message, log_level, exc)

    # Remove console handler so future logs only go to file
    main_logger.removeHandler(console_handler)
