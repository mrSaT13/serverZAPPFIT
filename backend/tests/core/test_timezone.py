"""Tests for core.timezone module."""

from datetime import UTC, datetime, timedelta, timezone
from unittest.mock import patch

import core.config as core_config
import core.timezone as core_timezone


class TestFormatAwareDatetime:
    """Tests for format_aware_datetime function."""

    def test_naive_datetime_assumes_utc(self):
        dt = datetime(2025, 1, 15, 10, 30, 0)
        result = core_timezone.format_aware_datetime(dt)
        assert result == "2025-01-15T10:30:00"

    def test_aware_datetime_utc(self):
        dt = datetime(2025, 1, 15, 10, 30, 0, tzinfo=UTC)
        result = core_timezone.format_aware_datetime(dt)
        assert result == "2025-01-15T10:30:00"

    def test_string_parsed_and_formatted(self):
        result = core_timezone.format_aware_datetime("2025-01-15T10:30:00")
        assert result == "2025-01-15T10:30:00"

    def test_custom_tz_name(self):
        dt = datetime(2025, 1, 15, 10, 30, 0, tzinfo=UTC)
        result = core_timezone.format_aware_datetime(dt, tz_name="America/New_York")
        assert result == "2025-01-15T05:30:00"

    def test_patched_tz_setting(self):
        dt = datetime(2025, 1, 15, 10, 30, 0, tzinfo=UTC)
        with patch.object(core_config.settings, "TZ", "America/New_York"):
            result = core_timezone.format_aware_datetime(dt)
        assert result == "2025-01-15T05:30:00"

    def test_output_format(self):
        dt = datetime(2025, 1, 15, 10, 30, 0, tzinfo=UTC)
        result = core_timezone.format_aware_datetime(dt)
        assert result == "2025-01-15T10:30:00"


class TestToUtcAware:
    """Tests for to_utc_aware function."""

    def test_none_returns_none(self):
        assert core_timezone.to_utc_aware(None) is None

    def test_naive_assumes_utc(self):
        dt = datetime(2025, 1, 15, 10, 30, 0)
        result = core_timezone.to_utc_aware(dt)
        assert result == datetime(2025, 1, 15, 10, 30, 0, tzinfo=UTC)

    def test_offset_converted_to_utc(self):
        dt = datetime(2026, 3, 28, 8, 19, 19, tzinfo=timezone(timedelta(hours=-7)))
        result = core_timezone.to_utc_aware(dt)
        assert result == datetime(2026, 3, 28, 15, 19, 19, tzinfo=UTC)

    def test_iso_string_parsed(self):
        result = core_timezone.to_utc_aware("2026-03-28T08:19:19-07:00")
        assert result == datetime(2026, 3, 28, 15, 19, 19, tzinfo=UTC)


class TestFormatUtc:
    """Tests for format_utc function."""

    def test_none_returns_empty_string(self):
        assert core_timezone.format_utc(None) == ""

    def test_naive_assumes_utc(self):
        dt = datetime(2025, 1, 15, 10, 30, 0)
        assert core_timezone.format_utc(dt) == "2025-01-15T10:30:00"

    def test_offset_converted_to_utc(self):
        dt = datetime(2026, 3, 28, 8, 19, 19, tzinfo=timezone(timedelta(hours=-7)))
        assert core_timezone.format_utc(dt) == "2026-03-28T15:19:19"

    def test_iso_string_with_offset(self):
        assert core_timezone.format_utc("2026-03-28T08:19:19-07:00") == "2026-03-28T15:19:19"
