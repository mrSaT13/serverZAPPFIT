"""Tests for application configuration validation."""

from unittest.mock import patch

import core.config as core_config


class TestSettingsStorageWarnings:
    """Tests for production storage configuration warnings."""

    def test_production_memory_storage_warns(self):
        """Test process-local security storage warns outside development."""
        with patch.object(
            core_config.core_logger,
            "print_to_log_and_console",
        ) as mock_log:
            core_config.Settings(
                ENVIRONMENT="production",
                RATE_LIMIT_ENABLED=True,
                RATE_LIMIT_STORAGE_URI="memory://",
                AUTH_SECURITY_STORAGE_URI=None,
                _env_file=None,
            )

        messages = [call.args[0] for call in mock_log.call_args_list]
        assert any("RATE_LIMIT_STORAGE_URI uses process-local memory" in message for message in messages)
        assert any("AUTH_SECURITY_STORAGE_URI resolves to process-local" in message for message in messages)

    def test_development_memory_storage_does_not_warn(self):
        """Test memory storage is allowed silently in development."""
        with patch.object(
            core_config.core_logger,
            "print_to_log_and_console",
        ) as mock_log:
            core_config.Settings(
                ENVIRONMENT="development",
                RATE_LIMIT_ENABLED=True,
                RATE_LIMIT_STORAGE_URI="memory://",
                AUTH_SECURITY_STORAGE_URI=None,
                _env_file=None,
            )

        messages = [call.args[0] for call in mock_log.call_args_list]
        assert not any("process-local memory" in message for message in messages)

    def test_production_redis_storage_does_not_warn(self):
        """Test Redis-backed storage does not emit memory warnings."""
        with patch.object(
            core_config.core_logger,
            "print_to_log_and_console",
        ) as mock_log:
            core_config.Settings(
                ENVIRONMENT="production",
                RATE_LIMIT_ENABLED=True,
                RATE_LIMIT_STORAGE_URI="redis://localhost:6379/0",
                AUTH_SECURITY_STORAGE_URI=None,
                _env_file=None,
            )

        messages = [call.args[0] for call in mock_log.call_args_list]
        assert not any("process-local memory" in message for message in messages)
