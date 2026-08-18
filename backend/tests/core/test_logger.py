"""Tests for core.logger module."""

import json
import logging
import sys
from unittest.mock import MagicMock, patch

import core.logger as core_logger


class TestRequestIdFilter:
    """Tests for RequestIdFilter class."""

    def test_adds_request_id_to_record(self):
        filter_ = core_logger.RequestIdFilter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="/f.py",
            lineno=1,
            msg="msg",
            args=(),
            exc_info=None,
        )
        with patch("core.logger.core_middleware_request_id.get_request_id", return_value="req-abc"):
            result = filter_.filter(record)
        assert result is True
        assert record.request_id == "req-abc"


class TestJsonFormatter:
    """Tests for JsonFormatter class."""

    def test_format_basic(self):
        formatter = core_logger.JsonFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="/f.py",
            lineno=1,
            msg="hello world",
            args=(),
            exc_info=None,
        )
        result = formatter.format(record)
        data = json.loads(result)
        assert data["level"] == "INFO"
        assert data["message"] == "hello world"
        assert data["logger"] == "test_logger"
        assert "request_id" not in data
        assert "exception" not in data
        assert "context" not in data
        assert "timestamp" in data

    def test_format_with_request_id(self):
        formatter = core_logger.JsonFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="/f.py",
            lineno=1,
            msg="msg",
            args=(),
            exc_info=None,
        )
        record.request_id = "req-123"
        result = formatter.format(record)
        data = json.loads(result)
        assert data["request_id"] == "req-123"

    def test_format_with_exc_info(self):
        formatter = core_logger.JsonFormatter()
        try:
            raise ValueError("test error detail")
        except ValueError:
            record = logging.LogRecord(
                name="test",
                level=logging.ERROR,
                pathname="/f.py",
                lineno=1,
                msg="error occurred",
                args=(),
                exc_info=sys.exc_info(),
            )
        result = formatter.format(record)
        data = json.loads(result)
        assert "exception" in data
        assert "ValueError" in data["exception"]
        assert "test error detail" in data["exception"]

    def test_format_with_context(self):
        formatter = core_logger.JsonFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="/f.py",
            lineno=1,
            msg="msg",
            args=(),
            exc_info=None,
        )
        record.user_id = 42
        record.action = "login"
        result = formatter.format(record)
        data = json.loads(result)
        assert data["context"]["user_id"] == 42
        assert data["context"]["action"] == "login"


class TestDevFormatter:
    """Tests for _DevFormatter class."""

    def test_format_basic(self):
        formatter = core_logger._DevFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="/f.py",
            lineno=1,
            msg="hello",
            args=(),
            exc_info=None,
        )
        record.request_id = ""
        result = formatter.format(record)
        assert "hello" in result
        assert "INFO" in result
        assert "test" in result

    def test_format_with_context(self):
        formatter = core_logger._DevFormatter()
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="/f.py",
            lineno=1,
            msg="hello",
            args=(),
            exc_info=None,
        )
        record.request_id = ""
        record.user_id = 42
        result = formatter.format(record)
        assert "hello" in result
        assert "user_id=42" in result


class TestBuildHandler:
    """Tests for _build_handler function."""

    def test_production_returns_stream_handler(self):
        with (
            patch("core.config.settings.ENVIRONMENT", "production"),
            patch("core.config.settings.LOGS_DIR", ""),
        ):
            handlers = core_logger._build_handler(logging.INFO)
        assert len(handlers) == 1
        handler = handlers[0]
        assert isinstance(handler, logging.StreamHandler)
        assert isinstance(handler.formatter, core_logger.JsonFormatter)
        assert handler.level == logging.INFO

    def test_demo_returns_stream_handler(self):
        with (
            patch("core.config.settings.ENVIRONMENT", "demo"),
            patch("core.config.settings.LOGS_DIR", ""),
        ):
            handlers = core_logger._build_handler(logging.WARNING)
        assert len(handlers) == 1
        handler = handlers[0]
        assert isinstance(handler, logging.StreamHandler)
        assert isinstance(handler.formatter, core_logger.JsonFormatter)

    def test_development_returns_file_handler(self, tmp_path):
        with (
            patch("core.config.settings.ENVIRONMENT", "development"),
            patch("core.config.settings.LOGS_DIR", str(tmp_path)),
        ):
            handlers = core_logger._build_handler(logging.DEBUG)
        assert len(handlers) == 1
        handler = handlers[0]
        assert isinstance(handler, logging.FileHandler)
        assert isinstance(handler.formatter, core_logger._DevFormatter)
        assert handler.level == logging.DEBUG


class TestReplaceHandlers:
    """Tests for _replace_handlers function."""

    def test_replaces_handlers(self):
        old_handler = MagicMock(spec=logging.Handler)
        new_handler = MagicMock(spec=logging.Handler)
        logger = logging.Logger("test_replace")
        logger.addHandler(old_handler)

        core_logger._replace_handlers((logger,), [new_handler])

        assert logger.handlers == [new_handler]
        assert logger.propagate is False

    def test_closes_old_handlers(self):
        old_handler = MagicMock(spec=logging.Handler)
        new_handler = MagicMock(spec=logging.Handler)
        logger = logging.Logger("test_close")
        logger.addHandler(old_handler)

        core_logger._replace_handlers((logger,), [new_handler])

        old_handler.close.assert_called_once()


class TestSetupMainLogger:
    """Tests for setup_main_logger function."""

    def test_returns_logger(self, tmp_path):
        with (
            patch("core.config.settings.ENVIRONMENT", "development"),
            patch("core.config.settings.LOG_LEVEL", "debug"),
            patch("core.config.settings.LOGS_DIR", str(tmp_path)),
        ):
            logger = core_logger.setup_main_logger()
        assert isinstance(logger, logging.Logger)
        assert logger.name == "main_logger"

    def test_logger_has_correct_level(self, tmp_path):
        with (
            patch("core.config.settings.ENVIRONMENT", "development"),
            patch("core.config.settings.LOG_LEVEL", "error"),
            patch("core.config.settings.LOGS_DIR", str(tmp_path)),
        ):
            logger = core_logger.setup_main_logger()
        assert logger.level == logging.ERROR

    def test_default_level_for_invalid_config(self, tmp_path):
        with (
            patch("core.config.settings.ENVIRONMENT", "development"),
            patch("core.config.settings.LOG_LEVEL", "invalid_level"),
            patch("core.config.settings.LOGS_DIR", str(tmp_path)),
        ):
            logger = core_logger.setup_main_logger()
        assert logger.level == logging.WARNING

    def test_safeuploads_audit_logger_propagates(self, tmp_path):
        with (
            patch("core.config.settings.ENVIRONMENT", "development"),
            patch("core.config.settings.LOG_LEVEL", "warning"),
            patch("core.config.settings.LOGS_DIR", str(tmp_path)),
        ):
            core_logger.setup_main_logger()
        assert logging.getLogger("safeuploads.audit").propagate is True


class TestGetMainLogger:
    """Tests for get_main_logger function."""

    def test_returns_main_logger(self):
        logger = core_logger.get_main_logger()
        assert isinstance(logger, logging.Logger)
        assert logger.name == "main_logger"


class TestPrintToLog:
    """Tests for print_to_log function."""

    def test_info_level(self):
        mock_logger = MagicMock()
        with patch("core.logger.get_main_logger", return_value=mock_logger):
            core_logger.print_to_log("info message", "info")
        mock_logger.info.assert_called_once_with("info message")

    def test_error_level(self):
        mock_logger = MagicMock()
        with patch("core.logger.get_main_logger", return_value=mock_logger):
            core_logger.print_to_log("error message", "error")
        mock_logger.error.assert_called_once_with("error message", exc_info=False)

    def test_error_with_exception(self):
        mock_logger = MagicMock()
        exc = ValueError("test error")
        with patch("core.logger.get_main_logger", return_value=mock_logger):
            core_logger.print_to_log("error message", "error", exc=exc)
        mock_logger.error.assert_called_once_with("error message", exc_info=True)

    def test_warning_level(self):
        mock_logger = MagicMock()
        with patch("core.logger.get_main_logger", return_value=mock_logger):
            core_logger.print_to_log("warning message", "warning")
        mock_logger.warning.assert_called_once_with("warning message")

    def test_debug_level(self):
        mock_logger = MagicMock()
        with patch("core.logger.get_main_logger", return_value=mock_logger):
            core_logger.print_to_log("debug message", "debug")
        mock_logger.debug.assert_called_once_with("debug message")

    def test_critical_level(self):
        mock_logger = MagicMock()
        with patch("core.logger.get_main_logger", return_value=mock_logger):
            core_logger.print_to_log("critical message", "critical")
        mock_logger.critical.assert_called_once_with("critical message")


class TestPrintToLogAndConsole:
    """Tests for print_to_log_and_console function."""

    def test_adds_and_removes_console_handler(self):
        mock_logger = MagicMock()
        with patch("core.logger.get_main_logger", return_value=mock_logger):
            core_logger.print_to_log_and_console("test message", "info")
        assert mock_logger.addHandler.called
        assert mock_logger.removeHandler.called
        added = mock_logger.addHandler.call_args[0][0]
        removed = mock_logger.removeHandler.call_args[0][0]
        assert added is removed
