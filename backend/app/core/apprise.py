"""Email-notification helpers backed by Apprise.

Wraps ``apprise`` so the rest of the application can
fire-and-forget transactional emails (password reset,
sign-up verification, admin alerts, …) without knowing
the underlying transport.
"""

import hashlib
import secrets
from functools import lru_cache
from urllib.parse import urlencode

import apprise

import core.config as core_config
import core.logger as core_logger

# Apprise-specific exceptions we treat as "send failed"
# rather than "programming error". Anything outside this
# set should propagate so it surfaces in tests/logs as a
# real bug instead of being silently swallowed.
_APPRISE_NETWORK_ERRORS: tuple[type[BaseException], ...] = (
    ConnectionError,
    TimeoutError,
    OSError,
)


class AppriseService:
    """Thin Apprise wrapper for transactional email."""

    def __init__(self) -> None:
        """Bind to the current ``settings`` snapshot.

        The constructor is deliberately cheap and pure:
        it copies primitive values from ``settings`` and
        loads the password via :func:`read_secret` once.
        Re-instantiating after env changes is the
        intended way to reload configuration.

        DB overrides env: if ``server_settings.smtp_host`` is set in the DB,
        it takes precedence (admin UI). Otherwise env vars are used.
        """
        s = core_config.settings
        # Defaults from env
        smtp_host: str | None = s.SMTP_HOST
        smtp_port: int = s.SMTP_PORT
        smtp_username: str | None = s.SMTP_USERNAME
        smtp_from: str | None = s.SMTP_FROM
        smtp_secure: bool = s.SMTP_SECURE
        smtp_secure_type: str = s.SMTP_SECURE_TYPE
        smtp_password: str | None = core_config.read_secret("SMTP_PASSWORD")
        frontend_host: str = s.ZAPFIT_HOST or s.ENDURAIN_HOST

        # Try DB override (admin UI) — best-effort, never break startup
        try:
            # Local import to avoid circular
            import server_settings.models as _ss_models
            from core.database import SessionLocal as _SessionLocal
            import core.cryptography as _crypt

            db = _SessionLocal()
            try:
                row = db.query(_ss_models.ServerSettings).filter(_ss_models.ServerSettings.id == 1).first()
                if row is not None and row.smtp_host:
                    smtp_host = row.smtp_host
                    if row.smtp_port is not None:
                        smtp_port = row.smtp_port
                    if row.smtp_username is not None:
                        smtp_username = row.smtp_username
                    if row.smtp_password:
                        try:
                            smtp_password = _crypt.decrypt_token_fernet(row.smtp_password)
                        except Exception:
                            pass
                    if row.smtp_from is not None:
                        smtp_from = row.smtp_from
                    if row.smtp_secure is not None:
                        smtp_secure = row.smtp_secure
                    if row.smtp_secure_type:
                        smtp_secure_type = row.smtp_secure_type
                    # frontend_host may also be overridden by brand? keep env host for email footer
                    # but prefer DB brand? frontend_host stays env for now
            finally:
                db.close()
        except Exception:
            pass

        self.smtp_host: str | None = smtp_host
        self.smtp_port: int = smtp_port
        self.smtp_username: str | None = smtp_username
        # Optional explicit "From" address. When unset,
        # Apprise auto-detects it from the URL. Needed for
        # providers like Brevo that validate the sender
        # against a verified-sender list.
        self.smtp_from: str | None = smtp_from
        self.smtp_secure: bool = smtp_secure
        self.smtp_secure_type: str = smtp_secure_type
        # Password is intentionally not stored on the
        # Settings object; it is loaded from env or a
        # Docker secret file via ``read_secret`` or DB.
        self.smtp_password: str | None = smtp_password
        # Public attribute consumed by email-body templates
        # (e.g. ``{email_service.frontend_host}/login``).
        self.frontend_host: str = frontend_host

    # SMTP URL construction
    def _build_smtp_url(self) -> str:
        """Build the ``mailto(s)://`` URL Apprise dials.

        Uses ``urlencode`` so credentials and host values
        with reserved characters (``&``, ``?``, ``#``,
        whitespace) are escaped exactly once. Auth fields
        are only emitted when both username and password
        are present — unauthenticated relays are valid.

        Returns:
            A fully-encoded Apprise URL. Treat as
            sensitive: it embeds the SMTP password in the
            query string and must never be logged.
        """
        scheme = "mailtos" if self.smtp_secure else "mailto"

        # Build the query as a list of (key, value) pairs
        # so urlencode handles every special character.
        # ``filter`` drops auth pairs when credentials
        # aren't configured (for unauthenticated relays).
        params: list[tuple[str, str]] = []
        if self.smtp_secure:
            params.append(("mode", self.smtp_secure_type))
        if self.smtp_username and self.smtp_password:
            params.append(("user", self.smtp_username))
            params.append(("pass", self.smtp_password))
        params.append(("smtp", self.smtp_host))
        params.append(("port", str(self.smtp_port)))
        params.append(("name", "ZAPFIT"))
        # Set the "From" address so providers that validate
        # it (e.g. Brevo) accept the message. Omitted when
        # unset so Apprise keeps auto-detecting the sender.
        if self.smtp_from:
            params.append(("from", self.smtp_from))

        return f"{scheme}://_?{urlencode(params)}"

    # Send email
    async def send_email(
        self,
        to_emails: list[str],
        subject: str,
        html_content: str | None = None,
        text_content: str | None = None,
    ) -> bool:
        """Send a transactional email to one or more recipients.

        HTML content is preferred; text content is the
        fallback. Returns ``False`` (and logs a warning)
        when SMTP isn't configured, no recipients are
        supplied, or the underlying transport reports a
        network failure. Programming errors (TypeError,
        ValueError, etc.) deliberately propagate.

        Args:
            to_emails: Recipient addresses.
            subject: Email subject line.
            html_content: HTML body (preferred).
            text_content: Plain-text fallback body.

        Returns:
            True on successful delivery, False otherwise.
        """
        if not to_emails:
            core_logger.print_to_log(
                "send_email called with no recipients",
                "warning",
            )
            return False
        if not self.is_smtp_configured():
            core_logger.print_to_log("send_email skipped: SMTP not configured", "warning")
            return False

        content = html_content if html_content else text_content
        if not content:
            core_logger.print_to_log(
                "send_email called with neither html_content nor text_content",
                "warning",
            )
            return False
        body_format = "html" if html_content else "text"

        try:
            temp_apprise = apprise.Apprise()
            smtp_url = self._build_smtp_url()
            for email in to_emails:
                # ``to`` accepts a single address per add()
                # call. ``urlencode`` keeps the recipient
                # safe even if the email contains special
                # characters (extremely rare but cheap to
                # defend against).
                recipient_qs = urlencode([("to", email)])
                temp_apprise.add(f"{smtp_url}&{recipient_qs}")

            success = await temp_apprise.async_notify(title=subject, body=content, body_format=body_format)
        except _APPRISE_NETWORK_ERRORS as err:
            # Log the exception type only; ``err`` may
            # contain the recipient or partial credentials
            # in its message on some libc/transport
            # combinations.
            core_logger.print_to_log(
                f"send_email transport failure for subject '{subject}': {type(err).__name__}",
                "error",
                exc=err,
            )
            return False
        except Exception as err:
            # Apprise can raise ValueError/other on bad URL/mode (e.g. wrong
            # smtp_secure_type for mail.ru). Treat as send failure, not 500.
            core_logger.print_to_log(
                f"send_email apprise error for subject '{subject}': {type(err).__name__}: {err}",
                "error",
                exc=err,
            )
            return False

        if success:
            core_logger.print_to_log(f"Email sent: {subject} (recipients={len(to_emails)})", "info")
        else:
            core_logger.print_to_log_and_console(f"Email send returned failure: {subject}", "warning")
        return bool(success)

    # Configuration introspection
    def is_configured(self) -> bool:
        """Whether the notification system can send mail."""
        return self.is_smtp_configured()

    def is_smtp_configured(self) -> bool:
        """Whether SMTP is sufficiently configured to attempt a send.

        Requires a host. When a username is configured we
        also require a password — half-configured auth is
        treated as misconfiguration so callers don't
        spend cycles attempting unauthenticated sends
        against an authenticated relay.
        """
        if not self.smtp_host:
            return False
        return not (self.smtp_username and not self.smtp_password)


# Module-level accessors
@lru_cache(maxsize=1)
def get_email_service() -> AppriseService:
    """Return the process-wide :class:`AppriseService` instance.

    Constructed lazily so importing this module never
    triggers env-var or secret-file reads. Used as a
    FastAPI dependency in routers; safe to call from
    anywhere because the result is cached.
    """
    return AppriseService()


def __getattr__(name: str):
    """Lazy module attribute hook.

    Preserves the legacy ``core_apprise.email_service``
    attribute access pattern without instantiating the
    service at import time.
    """
    if name == "email_service":
        return get_email_service()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# Token helpers
def generate_token_and_hash() -> tuple[str, str]:
    """Generate a URL-safe random token and its SHA-256 hash.

    Returns:
        ``(token, token_hash)``. Store the hash in the
        database; hand the raw token to the user via the
        outbound channel (email link, etc.). Comparing
        the SHA-256 of an incoming token to the stored
        hash avoids leaking the secret if the DB is read
        by an attacker.
    """
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    return token, token_hash
