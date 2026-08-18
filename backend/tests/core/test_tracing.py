"""Tests for core.tracing — OpenTelemetry setup."""

import os
from unittest.mock import MagicMock, patch


class TestTracingEnabled:
    """Tests for _tracing_enabled helper."""

    def test_returns_true_when_env_is_true(self):
        from core.tracing import _tracing_enabled

        with patch.dict(os.environ, {"JAEGER_ENABLED": "true"}):
            assert _tracing_enabled() is True

    def test_returns_true_when_env_is_1(self):
        from core.tracing import _tracing_enabled

        with patch.dict(os.environ, {"JAEGER_ENABLED": "1"}):
            assert _tracing_enabled() is True

    def test_returns_true_when_env_is_yes(self):
        from core.tracing import _tracing_enabled

        with patch.dict(os.environ, {"JAEGER_ENABLED": "yes"}):
            assert _tracing_enabled() is True

    def test_returns_false_when_env_is_false(self):
        from core.tracing import _tracing_enabled

        with patch.dict(os.environ, {"JAEGER_ENABLED": "false"}):
            assert _tracing_enabled() is False

    def test_returns_false_when_env_is_0(self):
        from core.tracing import _tracing_enabled

        with patch.dict(os.environ, {"JAEGER_ENABLED": "0"}):
            assert _tracing_enabled() is False

    def test_returns_false_when_env_is_no(self):
        from core.tracing import _tracing_enabled

        with patch.dict(os.environ, {"JAEGER_ENABLED": "no"}):
            assert _tracing_enabled() is False

    def test_returns_false_when_env_unset(self):
        from core.tracing import _tracing_enabled

        with patch.dict(os.environ, {}, clear=True):
            assert _tracing_enabled() is False


class TestSetupTracing:
    """Tests for setup_tracing function."""

    def test_returns_early_when_tracing_disabled(self):
        from core.tracing import setup_tracing

        app = MagicMock()

        with (
            patch("core.tracing._tracing_enabled", return_value=False),
            patch("core.tracing.FastAPIInstrumentor") as mock_instrumentor,
        ):
            setup_tracing(app)

        mock_instrumentor.instrument_app.assert_not_called()

    def test_instruments_app_when_tracing_enabled(self):
        from core.tracing import setup_tracing

        app = MagicMock()

        with (
            patch("core.tracing._tracing_enabled", return_value=True),
            patch.dict(os.environ, {}, clear=True),
            patch("core.tracing.TracerProvider") as mock_provider,
            patch("core.tracing.BatchSpanProcessor"),
            patch("core.tracing.OTLPSpanExporter"),
            patch("core.tracing.FastAPIInstrumentor") as mock_instrumentor,
            patch("core.tracing.trace") as mock_trace,
        ):
            mock_trace.get_tracer_provider.return_value = mock_provider.return_value
            setup_tracing(app)

        mock_instrumentor.instrument_app.assert_called_once_with(app)
