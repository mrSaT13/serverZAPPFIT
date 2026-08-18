"""Tests for CORS origin allow-list construction."""

from unittest.mock import patch

import core.config as core_config
import main


def _settings(**overrides):
    values = {
        "ENVIRONMENT": "production",
        "ENDURAIN_HOST": "http://localhost:8080",
        "ZAPFIT_HOST": "https://zapfit.example.com",
    }
    values.update(overrides)
    return core_config.Settings(**values)


def _patch_settings(settings):
    return patch("main.core_config.settings", settings)


def test_production_uses_hosts_and_explicit_origins():
    """Production keeps the domain hosts and adds explicit origins only."""
    settings = _settings(CORS_ALLOWED_ORIGINS=["http://192.168.1.50:8080", "http://192.168.1.50:5173"])
    with _patch_settings(settings):
        origins = main._build_cors_origins(is_development=False)

    assert "https://zapfit.example.com" in origins
    assert "http://192.168.1.50:8080" in origins
    assert "http://192.168.1.50:5173" in origins
    assert "http://localhost:5173" not in origins


def test_production_has_no_duplicates():
    """Duplicate origins are collapsed in production too."""
    settings = _settings(
        ZAPFIT_HOST="http://192.168.1.50:8080",
        CORS_ALLOWED_ORIGINS=["http://192.168.1.50:8080"],
    )
    with _patch_settings(settings):
        origins = main._build_cors_origins(is_development=False)

    assert origins.count("http://192.168.1.50:8080") == 1


def test_development_adds_localhost():
    """Development includes the localhost frontend/API ports."""
    with _patch_settings(_settings()):
        origins = main._build_cors_origins(is_development=True)

    assert "http://localhost:8080" in origins
    assert "http://localhost:5173" in origins
    assert "http://localhost:5174" in origins


@patch("main._dev_lan_origins", return_value=["http://192.168.1.50:8080", "http://192.168.1.50:5173"])
def test_development_adds_lan_origins(mock_lan):
    """Development adds the machine's LAN IP origins."""
    with _patch_settings(_settings()):
        origins = main._build_cors_origins(is_development=True)

    assert "http://192.168.1.50:8080" in origins
    assert "http://192.168.1.50:5173" in origins


def test_empty_hosts_are_filtered():
    """Empty origin strings never reach the allow-list."""
    settings = _settings(ENDURAIN_HOST="", ZAPFIT_HOST="", CORS_ALLOWED_ORIGINS=[])
    with _patch_settings(settings):
        origins = main._build_cors_origins(is_development=False)

    assert origins == []


def test_dev_lan_origins_shape():
    """_dev_lan_origins returns well-formed http origins."""
    origins = main._dev_lan_origins()

    assert origins
    for origin in origins:
        assert origin.startswith("http://")
        assert origin.rsplit(":", 1)[1] in {"8080", "5173", "5174"}
