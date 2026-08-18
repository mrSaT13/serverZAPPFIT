"""Centralized timezone conversion utilities."""

from datetime import datetime
from zoneinfo import ZoneInfo

import core.config as core_config

# ISO 8601 datetime format without offset, used for the
# naive UTC wall-clock strings persisted by file parsers.
_DT_FMT = "%Y-%m-%dT%H:%M:%S"


def to_utc_aware(dt: datetime | str | None) -> datetime | None:
    """
    Normalize a datetime or ISO string to UTC-aware.

    Parses ISO 8601 strings and attaches UTC to naive
    datetimes (the import parsers emit naive UTC wall
    clock values). Ensures stored timestamps carry an
    explicit UTC offset instead of relying on the
    database session timezone.

    Args:
        dt: A datetime, ISO 8601 string, or None.

    Returns:
        A UTC-aware datetime, or None if dt is None.
    """
    if dt is None:
        return None
    if isinstance(dt, str):
        dt = datetime.fromisoformat(dt)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))
    return dt.astimezone(ZoneInfo("UTC"))


def format_utc(dt: datetime | str | None) -> str:
    """
    Format a datetime as a UTC ISO 8601 string (no offset).

    File timestamps may carry a non-UTC offset (e.g.
    2026-03-28T08:19:19-07:00). Converting to UTC before
    formatting preserves the actual instant; without it the
    offset is silently dropped and the wall-clock is stored
    as if it were UTC. Naive datetimes are assumed to be UTC.

    Args:
        dt: A datetime, ISO 8601 string, or None.

    Returns:
        UTC ISO 8601 string without an offset, or an empty
        string if dt is None.
    """
    aware = to_utc_aware(dt)
    return aware.strftime(_DT_FMT) if aware else ""


def format_aware_datetime(
    dt: datetime | str,
    tz_name: str | None = None,
) -> str:
    """
    Convert a datetime to a timezone-aware string.

    Assumes UTC if the datetime has no tzinfo.
    Converts to the specified timezone (or the
    server default) and formats as ISO 8601 without
    offset.

    Args:
        dt: A datetime object or ISO 8601 string.
        tz_name: IANA timezone name. Falls back to
            the server TZ setting if None.

    Returns:
        Formatted datetime string without offset.
    """
    if isinstance(dt, str):
        dt = datetime.fromisoformat(dt)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))

    timezone = ZoneInfo(tz_name) if tz_name else ZoneInfo(core_config.settings.TZ)

    return dt.astimezone(timezone).strftime("%Y-%m-%dT%H:%M:%S")
