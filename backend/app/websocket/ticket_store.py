"""WebSocket authentication ticket store."""

import secrets
from datetime import UTC, datetime, timedelta
from threading import Lock
from typing import NoReturn, Protocol, cast, runtime_checkable

from redis import Redis, RedisError

import core.config as core_config
import core.logger as core_logger
import core.redis as core_redis

TICKET_TTL_SECONDS = 30
_TICKET_KEY_PREFIX = "ws:ticket:"


class WsTicketStoreUnavailableError(RuntimeError):
    """
    Raised when WS ticket storage cannot be reached.

    Attributes:
        None.
    """


def _raise_store_unavailable(operation: str, err: RedisError) -> NoReturn:
    """
    Raise a sanitized WS ticket storage exception.

    Args:
        operation: Storage operation that failed.
        err: Redis client exception.

    Raises:
        WsTicketStoreUnavailableError: Always raised.
    """
    core_redis.raise_storage_unavailable_as(
        WsTicketStoreUnavailableError,
        display_name="WS ticket storage",
        operation=operation,
        err=err,
    )


@runtime_checkable
class WsTicketStoreProtocol(Protocol):
    """
    Contract for WS ticket stores (memory or Redis).

    Attributes:
        None.
    """

    def create_ticket(self, user_id: int) -> str: ...

    def consume_ticket(self, ticket: str) -> int | None: ...


class WsTicketStore:
    """
    In-memory, short-lived, single-use ticket store for WebSocket auth.

    Attributes:
        _store: Mapping of ticket to (user_id, expires_at).
        _lock: Thread-safety lock.
    """

    def __init__(self) -> None:
        """Initialize the ticket store."""
        self._store: dict[str, tuple[int, datetime]] = {}
        self._lock = Lock()

    def create_ticket(self, user_id: int) -> str:
        """
        Issue a new short-lived ticket for a user.

        Args:
            user_id: Authenticated user ID.

        Returns:
            Opaque, URL-safe ticket string.
        """
        ticket = secrets.token_urlsafe(32)
        expires_at = datetime.now(UTC) + timedelta(seconds=TICKET_TTL_SECONDS)
        with self._lock:
            self._cleanup_expired_locked()
            self._store[ticket] = (user_id, expires_at)
        return ticket

    def consume_ticket(self, ticket: str) -> int | None:
        """
        Validate and consume a ticket (single-use).

        Args:
            ticket: Opaque ticket string from query parameter.

        Returns:
            Authenticated user ID, or None if invalid/expired.
        """
        with self._lock:
            entry = self._store.pop(ticket, None)
        if entry is None:
            return None
        user_id, expires_at = entry
        if datetime.now(UTC) > expires_at:
            return None
        return user_id

    def _cleanup_expired_locked(self) -> None:
        """
        Remove expired tickets while holding the lock.

        Args:
            None.

        Returns:
            None.
        """
        now = datetime.now(UTC)
        expired = [k for k, (_, exp) in self._store.items() if now > exp]
        for k in expired:
            del self._store[k]


class RedisWsTicketStore:
    """
    Redis-backed, short-lived, single-use ticket store for WebSocket auth.

    Uses Redis SET with EX (TTL) and NX (collision guard) for atomic
    creation and GETDEL for atomic single-use consumption.

    Attributes:
        _redis: Redis client used for storage.
    """

    def __init__(self, redis_client: Redis) -> None:
        """
        Initialize the Redis-backed ticket store.

        Args:
            redis_client: Redis client used for storage.
        """
        self._redis = redis_client

    def create_ticket(self, user_id: int) -> str:
        """
        Issue a new short-lived ticket for a user.

        Args:
            user_id: Authenticated user ID.

        Returns:
            Opaque, URL-safe ticket string.

        Raises:
            WsTicketStoreUnavailableError: When Redis is unreachable.
        """
        try:
            for _ in range(3):
                ticket = secrets.token_urlsafe(32)
                key = f"{_TICKET_KEY_PREFIX}{ticket}"
                if self._redis.set(key, str(user_id), ex=TICKET_TTL_SECONDS, nx=True):
                    return ticket
        except RedisError as err:
            _raise_store_unavailable("create_ticket", err)
        raise RuntimeError(  # pragma: no cover
            "Failed to generate a unique WS ticket after 3 attempts"
        )

    def consume_ticket(self, ticket: str) -> int | None:
        """
        Validate and consume a ticket (single-use).

        Args:
            ticket: Opaque ticket string from query parameter.

        Returns:
            Authenticated user ID, or None if invalid/expired/unknown.

        Raises:
            WsTicketStoreUnavailableError: When Redis is unreachable.
        """
        key = f"{_TICKET_KEY_PREFIX}{ticket}"
        try:
            value = cast("str | None", self._redis.getdel(key))
        except RedisError as err:
            _raise_store_unavailable("consume_ticket", err)
        if value is None:
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            core_logger.print_to_log(
                "Unexpected non-integer value in WS ticket store",
                "warning",
            )
            return None


def get_ws_ticket_storage_uri() -> str:
    """
    Resolve the configured WS ticket storage URI.

    Falls back to the auth security storage URI, which itself
    falls back to the rate-limit URI and then memory://.

    Returns:
        Storage URI string.

    Raises:
        None.
    """
    return core_config.settings.resolved_auth_security_storage_uri


def create_ws_ticket_store(
    storage_uri: str,
) -> WsTicketStore | RedisWsTicketStore:
    """
    Create a WS ticket store for the configured backend.

    Args:
        storage_uri: Storage URI selecting memory or Redis.

    Returns:
        WsTicketStore or RedisWsTicketStore instance.

    Raises:
        RuntimeError: When Redis cannot be initialized.
        ValueError: When the storage URI scheme is unsupported.
    """
    return cast(
        WsTicketStore | RedisWsTicketStore,
        core_redis.select_storage_backend(
            storage_uri,
            purpose="WS ticket storage",
            scheme_error_label="WS_TICKET_STORAGE_URI",
            memory_factory=WsTicketStore,
            redis_factory=RedisWsTicketStore,
        ),
    )


_ws_ticket_store: WsTicketStore | RedisWsTicketStore = create_ws_ticket_store(get_ws_ticket_storage_uri())


def get_ws_ticket_store() -> WsTicketStore | RedisWsTicketStore:
    """
    FastAPI dependency providing the singleton ticket store.

    Returns:
        The global WsTicketStore or RedisWsTicketStore instance.
    """
    return _ws_ticket_store
