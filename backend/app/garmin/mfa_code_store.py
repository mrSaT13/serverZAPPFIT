"""Temporary Garmin MFA code storage for cross-request handoff.

The Garmin Connect link flow is asynchronous: the backend starts a blocking
login in a thread that eventually calls back for an MFA code, while the user
submits that code via a separate HTTP request.  In a multi-worker deployment
these two requests may land on different processes, so process-local dicts are
insufficient.  This module provides memory and Redis backends selected by the
same ``AUTH_SECURITY_STORAGE_URI`` / ``RATE_LIMIT_STORAGE_URI`` config used
by the auth security stores.

Interface::

    add_code(user_id, code)   - store the MFA code for user_id
    get_code(user_id)         - retrieve it (does NOT delete)
    delete_code(user_id)      - remove it after consumption
    has_code(user_id)         - check whether a live code exists
    clear_all()               - remove all codes (for tests / admin)
"""

import threading
import time
from typing import NoReturn

from redis import Redis, RedisError

import core.config as core_config
import core.logger as core_logger
import core.redis as core_redis

_REDIS_GARMIN_MFA_KEY_PREFIX = "endurain:garmin:mfa:code"
# TTL must exceed the 65-second blocking_login timeout in garmin/utils.py.
_DEFAULT_TTL_SECONDS: int = 90


class GarminMFACodeStoreUnavailableError(RuntimeError):
    """
    Raised when the Garmin MFA code storage backend cannot be reached.

    Attributes:
        None.
    """


def _raise_store_unavailable(operation: str, err: RedisError) -> NoReturn:
    """
    Raise a sanitized store-unavailable exception.

    Args:
        operation: Storage operation that failed.
        err: Redis client exception.

    Raises:
        GarminMFACodeStoreUnavailableError: Always raised.
    """
    core_redis.raise_storage_unavailable_as(
        GarminMFACodeStoreUnavailableError,
        display_name="Garmin MFA code storage",
        operation=operation,
        err=err,
    )


def _get_storage_uri() -> str:
    """
    Resolve the storage URI for the Garmin MFA code store.

    Returns:
        AUTH_SECURITY_STORAGE_URI, or RATE_LIMIT_STORAGE_URI, or ``memory://``.

    Raises:
        None.
    """
    return core_config.settings.resolved_auth_security_storage_uri


def _user_id_digest(user_id: int) -> str:
    """
    Hash a user ID for Redis key names.

    Args:
        user_id: User ID to hash.

    Returns:
        SHA-256 hex digest.

    Raises:
        None.
    """
    return core_redis.sha256_key_digest(str(user_id))


class GarminMFACodeStore:
    """
    Thread-safe in-memory storage for temporary Garmin MFA codes with TTL.

    Attributes:
        _store: Mapping of user_id to ``{"code": str, "expires_at": float}``.
        _lock: Re-entrant lock for thread safety.
        _ttl_seconds: Code lifetime in seconds.
        _cleanup_thread: Background daemon thread that evicts expired entries.
    """

    def __init__(self, ttl_seconds: int = _DEFAULT_TTL_SECONDS) -> None:
        """
        Initialize the in-memory Garmin MFA code store.

        Args:
            ttl_seconds: How long each stored code remains valid.
        """
        self._store: dict[int, dict] = {}
        self._lock = threading.RLock()
        self._ttl_seconds = ttl_seconds
        self._cleanup_thread: threading.Thread | None = None
        self._start_cleanup_thread()

    def _start_cleanup_thread(self) -> None:
        """Start the background TTL-cleanup daemon if not already running."""
        if self._cleanup_thread is None or not self._cleanup_thread.is_alive():
            self._cleanup_thread = threading.Thread(
                target=self._cleanup_expired_codes,
                daemon=True,
                name="GarminMFACode-Cleanup",
            )
            self._cleanup_thread.start()

    def _cleanup_expired_codes(self) -> None:
        """Periodically remove expired entries from the in-memory store."""
        while True:
            try:
                current_time = time.time()
                with self._lock:
                    expired = [uid for uid, data in self._store.items() if current_time > data["expires_at"]]
                    for uid in expired:
                        del self._store[uid]
                        core_logger.print_to_log(
                            f"Cleaned up expired Garmin MFA code for user {uid}",
                            "debug",
                        )
                time.sleep(30)
            except Exception as err:
                core_logger.print_to_log(
                    f"Error in Garmin MFA code cleanup thread: {type(err).__name__}",
                    "error",
                    exc=err,
                )
                time.sleep(60)

    def add_code(self, user_id: int, code: str) -> None:
        """
        Store a Garmin MFA code for user_id with TTL.

        Args:
            user_id: Authenticated user ID.
            code: The MFA code submitted by the user.

        Raises:
            None.
        """
        with self._lock:
            self._store[user_id] = {
                "code": code,
                "expires_at": time.time() + self._ttl_seconds,
            }
        core_logger.print_to_log(f"Stored Garmin MFA code for user {user_id}", "debug")

    def get_code(self, user_id: int) -> str | None:
        """
        Retrieve a Garmin MFA code if it has not expired.

        Args:
            user_id: Authenticated user ID.

        Returns:
            The stored code string, or None if missing or expired.

        Raises:
            None.
        """
        with self._lock:
            if user_id not in self._store:
                return None
            data = self._store[user_id]
            if time.time() > data["expires_at"]:
                del self._store[user_id]
                return None
            return str(data["code"])

    def delete_code(self, user_id: int) -> None:
        """
        Remove the Garmin MFA code for user_id.

        Args:
            user_id: Authenticated user ID.

        Raises:
            None.
        """
        with self._lock:
            self._store.pop(user_id, None)

    def has_code(self, user_id: int) -> bool:
        """
        Return True when a non-expired code exists for user_id.

        Args:
            user_id: Authenticated user ID.

        Returns:
            True if a valid code is stored, False otherwise.

        Raises:
            None.
        """
        with self._lock:
            if user_id not in self._store:
                return False
            if time.time() > self._store[user_id]["expires_at"]:
                del self._store[user_id]
                return False
            return True

    def clear_all(self) -> None:
        """
        Remove all stored codes (used in tests and admin resets).

        Raises:
            None.
        """
        with self._lock:
            self._store.clear()

    def __repr__(self) -> str:
        with self._lock:
            return f"GarminMFACodeStore(active={len(self._store)}, ttl={self._ttl_seconds}s)"


class RedisGarminMFACodeStore:
    """
    Redis-backed storage for temporary Garmin MFA codes.

    Attributes:
        _redis: Redis client used for storage.
        _ttl_seconds: Code lifetime in seconds (used as Redis ``ex`` value).
    """

    def __init__(self, redis_client: Redis, ttl_seconds: int = _DEFAULT_TTL_SECONDS) -> None:
        """
        Initialize the Redis Garmin MFA code store.

        Args:
            redis_client: Connected Redis client.
            ttl_seconds: How long each stored code remains valid.
        """
        self._redis = redis_client
        self._ttl_seconds = ttl_seconds

    def _key(self, user_id: int) -> str:
        """
        Build the Redis key for a user's pending MFA code.

        Args:
            user_id: Authenticated user ID.

        Returns:
            Namespaced Redis key string.

        Raises:
            None.
        """
        return f"{_REDIS_GARMIN_MFA_KEY_PREFIX}:{_user_id_digest(user_id)}"

    def add_code(self, user_id: int, code: str) -> None:
        """
        Store a Garmin MFA code in Redis with TTL.

        Args:
            user_id: Authenticated user ID.
            code: The MFA code submitted by the user.

        Raises:
            GarminMFACodeStoreUnavailableError: When Redis access fails.
        """
        try:
            self._redis.set(self._key(user_id), code, ex=self._ttl_seconds)
        except RedisError as err:
            _raise_store_unavailable("add Garmin MFA code", err)
        core_logger.print_to_log(f"Stored Garmin MFA code for user {user_id} in Redis", "debug")

    def get_code(self, user_id: int) -> str | None:
        """
        Retrieve a Garmin MFA code from Redis.

        Args:
            user_id: Authenticated user ID.

        Returns:
            The stored code string, or None if missing or expired.

        Raises:
            GarminMFACodeStoreUnavailableError: When Redis access fails.
        """
        try:
            value = self._redis.get(self._key(user_id))
        except RedisError as err:
            _raise_store_unavailable("get Garmin MFA code", err)
        if value is None:
            return None
        return value.decode() if isinstance(value, bytes) else str(value)

    def delete_code(self, user_id: int) -> None:
        """
        Remove the Garmin MFA code for user_id from Redis.

        If deletion fails, the entry will expire via TTL anyway.

        Args:
            user_id: Authenticated user ID.

        Raises:
            None.
        """
        try:
            self._redis.delete(self._key(user_id))
        except RedisError as err:
            core_logger.print_to_log(
                "Failed to delete Garmin MFA code from Redis; entry will expire naturally via TTL",
                "warning",
                exc=err,
            )

    def has_code(self, user_id: int) -> bool:
        """
        Return True when a non-expired code exists for user_id in Redis.

        Args:
            user_id: Authenticated user ID.

        Returns:
            True if a valid code is stored, False otherwise.

        Raises:
            GarminMFACodeStoreUnavailableError: When Redis access fails.
        """
        try:
            return self._redis.get(self._key(user_id)) is not None
        except RedisError as err:
            _raise_store_unavailable("check Garmin MFA code", err)

    def clear_all(self) -> None:
        """
        Remove all Garmin MFA codes from Redis storage.

        Raises:
            GarminMFACodeStoreUnavailableError: When Redis access fails.
        """
        key_pattern = f"{_REDIS_GARMIN_MFA_KEY_PREFIX}:*"
        try:
            core_redis.delete_matching_keys(self._redis, key_pattern)
        except RedisError as err:
            _raise_store_unavailable("clear Garmin MFA codes", err)

    def __repr__(self) -> str:
        return f"RedisGarminMFACodeStore(ttl={self._ttl_seconds}s)"


GarminMFACodeStoreBackend = GarminMFACodeStore | RedisGarminMFACodeStore


def create_garmin_mfa_code_store(
    storage_uri: str,
) -> GarminMFACodeStoreBackend:
    """
    Create a Garmin MFA code store for the configured backend.

    Args:
        storage_uri: Storage URI selecting ``memory://`` or a Redis URL.

    Returns:
        A :class:`GarminMFACodeStore` or :class:`RedisGarminMFACodeStore` instance.

    Raises:
        RuntimeError: When Redis cannot be initialised.
        ValueError: When the storage URI scheme is unsupported.
    """
    return core_redis.select_storage_backend(
        storage_uri,
        purpose="Garmin MFA code storage",
        scheme_error_label="Garmin MFA code storage URI",
        memory_factory=GarminMFACodeStore,
        redis_factory=RedisGarminMFACodeStore,
    )


def get_garmin_mfa_code_store() -> GarminMFACodeStoreBackend:
    """
    Return the module-level Garmin MFA code store instance.

    Returns:
        The global :data:`garmin_mfa_code_store` singleton.

    Raises:
        None.
    """
    return garmin_mfa_code_store


garmin_mfa_code_store = create_garmin_mfa_code_store(_get_storage_uri())
