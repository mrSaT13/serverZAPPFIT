"""Tests for core.apprise module."""

import hashlib
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import core.apprise as core_apprise


class TestAppriseServiceInit:
    """Tests for AppriseService.__init__."""

    def test_reads_smtp_settings(self):
        service = core_apprise.AppriseService()
        assert hasattr(service, "smtp_host")
        assert hasattr(service, "smtp_port")
        assert hasattr(service, "smtp_username")
        assert hasattr(service, "smtp_from")
        assert hasattr(service, "smtp_secure")
        assert hasattr(service, "smtp_secure_type")
        assert hasattr(service, "smtp_password")
        assert hasattr(service, "frontend_host")


class TestBuildSmtpUrl:
    """Tests for _build_smtp_url method."""

    def test_secure_with_auth(self):
        service = core_apprise.AppriseService()
        service.smtp_secure = True
        service.smtp_secure_type = "starttls"
        service.smtp_username = "user@example.com"
        service.smtp_password = "secret123"
        service.smtp_host = "smtp.example.com"
        service.smtp_port = 587

        url = service._build_smtp_url()
        assert url.startswith("mailtos://")
        assert "mode=starttls" in url
        assert "user=user%40example.com" in url
        assert "pass=secret123" in url
        assert "smtp=smtp.example.com" in url
        assert "port=587" in url
        assert "name=ZAPFIT" in url

    def test_secure_no_auth(self):
        service = core_apprise.AppriseService()
        service.smtp_secure = True
        service.smtp_secure_type = "ssl"
        service.smtp_username = ""
        service.smtp_password = None
        service.smtp_host = "smtp.example.com"
        service.smtp_port = 465

        url = service._build_smtp_url()
        assert url.startswith("mailtos://")
        assert "mode=ssl" in url
        assert "user=" not in url
        assert "pass=" not in url

    def test_not_secure(self):
        service = core_apprise.AppriseService()
        service.smtp_secure = False
        service.smtp_username = ""
        service.smtp_password = None
        service.smtp_host = "smtp.example.com"
        service.smtp_port = 25

        url = service._build_smtp_url()
        assert url.startswith("mailto://")
        assert "mode=" not in url

    def test_with_smtp_secure_type(self):
        service = core_apprise.AppriseService()
        service.smtp_secure = True
        service.smtp_secure_type = "ssl"
        service.smtp_username = ""
        service.smtp_password = None
        service.smtp_host = "smtp.example.com"
        service.smtp_port = 465

        url = service._build_smtp_url()
        assert "mode=ssl" in url

    def test_with_from_address(self):
        service = core_apprise.AppriseService()
        service.smtp_secure = True
        service.smtp_secure_type = "starttls"
        service.smtp_username = "login@example.com"
        service.smtp_password = "secret123"
        service.smtp_host = "smtp-relay.brevo.com"
        service.smtp_port = 587
        service.smtp_from = "sender@example.com"

        url = service._build_smtp_url()
        assert "from=sender%40example.com" in url

    def test_without_from_address(self):
        service = core_apprise.AppriseService()
        service.smtp_secure = True
        service.smtp_secure_type = "starttls"
        service.smtp_username = "login@example.com"
        service.smtp_password = "secret123"
        service.smtp_host = "smtp.example.com"
        service.smtp_port = 587
        service.smtp_from = None

        url = service._build_smtp_url()
        assert "from=" not in url


class TestIsSmtpConfigured:
    """Tests for is_smtp_configured method."""

    def test_with_host_returns_true(self):
        service = core_apprise.AppriseService()
        service.smtp_host = "smtp.example.com"
        service.smtp_username = None
        service.smtp_password = None
        assert service.is_smtp_configured() is True

    def test_without_host_returns_false(self):
        service = core_apprise.AppriseService()
        service.smtp_host = ""
        assert service.is_smtp_configured() is False

    def test_with_username_no_password_returns_false(self):
        service = core_apprise.AppriseService()
        service.smtp_host = "smtp.example.com"
        service.smtp_username = "user"
        service.smtp_password = ""
        assert service.is_smtp_configured() is False


class TestIsConfigured:
    """Tests for is_configured method."""

    def test_delegates_to_is_smtp_configured(self):
        service = core_apprise.AppriseService()
        service.smtp_host = "smtp.example.com"
        assert service.is_configured() is True

        service.smtp_host = ""
        assert service.is_configured() is False


class TestSendEmail:
    """Tests for send_email method."""

    async def test_no_recipients_returns_false(self):
        service = core_apprise.AppriseService()
        result = await service.send_email([], "subject", html_content="<p>Hi</p>")
        assert result is False

    async def test_smtp_not_configured_returns_false(self):
        service = core_apprise.AppriseService()
        service.smtp_host = ""
        result = await service.send_email(["test@example.com"], "subject", html_content="<p>Hi</p>")
        assert result is False

    async def test_no_content_returns_false(self):
        service = core_apprise.AppriseService()
        service.smtp_host = "smtp.example.com"
        result = await service.send_email(["test@example.com"], "subject")
        assert result is False

    async def test_text_content_is_used_when_no_html(self):
        service = core_apprise.AppriseService()
        service.smtp_host = "smtp.example.com"
        service.smtp_port = 587
        service.smtp_username = ""
        service.smtp_password = None
        service.smtp_secure = False
        service.smtp_secure_type = "starttls"
        with patch("core.apprise.apprise.Apprise") as mock_cls:
            mock_instance = MagicMock()

            async def _notify(*, title, body, body_format):
                assert body_format == "text"
                return True

            mock_instance.async_notify = _notify
            mock_cls.return_value = mock_instance
            result = await service.send_email(["test@example.com"], "subject", text_content="plain text")
        assert result is True

    async def test_successful_send_returns_true(self):
        service = core_apprise.AppriseService()
        service.smtp_host = "smtp.example.com"
        service.smtp_port = 587
        service.smtp_username = ""
        service.smtp_password = None
        service.smtp_secure = False
        service.smtp_secure_type = "starttls"
        with patch("core.apprise.apprise.Apprise") as mock_cls:
            mock_instance = MagicMock()
            mock_instance.async_notify = AsyncMock(return_value=True)
            mock_cls.return_value = mock_instance
            result = await service.send_email(
                ["user@example.com"],
                "Welcome",
                html_content="<h1>Hi</h1>",
            )
        assert result is True
        mock_instance.async_notify.assert_awaited_once()

    async def test_failed_send_returns_false(self):
        service = core_apprise.AppriseService()
        service.smtp_host = "smtp.example.com"
        service.smtp_port = 587
        service.smtp_username = ""
        service.smtp_password = None
        service.smtp_secure = False
        service.smtp_secure_type = "starttls"
        with patch("core.apprise.apprise.Apprise") as mock_cls:
            mock_instance = MagicMock()
            mock_instance.async_notify = AsyncMock(return_value=False)
            mock_cls.return_value = mock_instance
            result = await service.send_email(
                ["user@example.com"],
                "Welcome",
                html_content="<h1>Hi</h1>",
            )
        assert result is False

    async def test_network_error_returns_false(self):
        service = core_apprise.AppriseService()
        service.smtp_host = "smtp.example.com"
        service.smtp_port = 587
        service.smtp_username = ""
        service.smtp_password = None
        service.smtp_secure = False
        service.smtp_secure_type = "starttls"
        with patch("core.apprise.apprise.Apprise") as mock_cls:
            mock_instance = MagicMock()
            mock_instance.async_notify = AsyncMock(side_effect=ConnectionError("connection refused"))
            mock_cls.return_value = mock_instance
            result = await service.send_email(
                ["user@example.com"],
                "Welcome",
                html_content="<h1>Hi</h1>",
            )
        assert result is False

    async def test_multiple_recipients(self):
        service = core_apprise.AppriseService()
        service.smtp_host = "smtp.example.com"
        service.smtp_port = 587
        service.smtp_username = ""
        service.smtp_password = None
        service.smtp_secure = False
        service.smtp_secure_type = "starttls"
        with patch("core.apprise.apprise.Apprise") as mock_cls:
            mock_instance = MagicMock()
            mock_instance.async_notify = AsyncMock(return_value=True)
            mock_cls.return_value = mock_instance
            result = await service.send_email(
                ["a@example.com", "b@example.com"],
                "News",
                html_content="<p>Hi</p>",
            )
        assert result is True
        assert mock_instance.add.call_count == 2


class TestGetEmailService:
    """Tests for get_email_service function."""

    def setup_method(self):
        core_apprise.get_email_service.cache_clear()

    def test_returns_apprise_service_instance(self):
        service = core_apprise.get_email_service()
        assert isinstance(service, core_apprise.AppriseService)

    def test_cached_by_lru_cache(self):
        core_apprise.get_email_service.cache_clear()
        service1 = core_apprise.get_email_service()
        service2 = core_apprise.get_email_service()
        assert service1 is service2


class TestModuleGetAttr:
    """Tests for module __getattr__."""

    def setup_method(self):
        core_apprise.get_email_service.cache_clear()

    def test_returns_email_service(self):
        service = core_apprise.email_service
        assert isinstance(service, core_apprise.AppriseService)

    def test_raises_attribute_error_for_unknown(self):
        with pytest.raises(AttributeError):
            _ = core_apprise.non_existent


class TestGenerateTokenAndHash:
    """Tests for generate_token_and_hash function."""

    def test_returns_tuple(self):
        token, token_hash = core_apprise.generate_token_and_hash()
        assert isinstance(token, str)
        assert isinstance(token_hash, str)

    def test_token_is_url_safe(self):
        token, _ = core_apprise.generate_token_and_hash()
        assert len(token) > 40
        assert all(c.isalnum() or c in "-_" for c in token)

    def test_hash_is_sha256_of_token(self):
        token, token_hash = core_apprise.generate_token_and_hash()
        expected_hash = hashlib.sha256(token.encode()).hexdigest()
        assert token_hash == expected_hash

    def test_token_is_32_bytes(self):
        token, _ = core_apprise.generate_token_and_hash()
        import base64

        decoded = base64.urlsafe_b64decode(token + "==")
        assert len(decoded) == 32
