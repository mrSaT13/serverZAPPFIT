"""Redis connection utilities."""

from collections.abc import Callable
from typing import NoReturn

from redis import Redis, RedisError

import core.hashing as core_hashing
import core.logger as core_logger

DEFAULT_REDIS_SOCKET_TIMEOUT_SECONDS: float = 2.0


class RedisStorageUnavailableError(RuntimeError):
    """
    Raised when Redis-backed storage cannot be reached.

    Attributes:
        None.
    """


def raise_redis_storage_unavailable(
    purpose: str,
    operation: str,
    err: RedisError,
) -> NoReturn:
    """
    Raise a sanitized Redis storage outage exception.

    Args:
        purpose: Human-readable Redis storage purpose.
        operation: Storage operation that failed.
        err: Redis client exception.

    Raises:
        RedisStorageUnavailableError: Always raised.
    """
    core_logger.print_to_log(
        f"Redis operation failed for {purpose}: {operation}",
        "error",
        exc=err,
    )
    raise RedisStorageUnavailableError(f"Redis storage unavailable for {purpose}") from err


def is_redis_storage_uri(storage_uri: str) -> bool:
    """
    Check whether a storage URI selects Redis.

    Args:
        storage_uri: Storage URI from configuration.

    Returns:
        True when the URI selects Redis storage.

    Raises:
        None.
    """
    normalized_uri = storage_uri.strip().lower()
    return normalized_uri.startswith(("redis://", "rediss://", "unix://"))


def is_memory_storage_uri(storage_uri: str) -> bool:
    """
    Check whether a storage URI selects process-local memory.

    Args:
        storage_uri: Storage URI from configuration.

    Returns:
        True when the URI selects memory storage.

    Raises:
        None.
    """
    return storage_uri.strip().lower().startswith("memory://")


def delete_matching_keys(
    redis_client: Redis,
    key_pattern: str,
    scan_count: int = 100,
) -> int:
    """
    Delete Redis keys matching a scan pattern in small batches.

    Args:
        redis_client: Redis client used for deletion.
        key_pattern: Redis glob-style key pattern.
        scan_count: Requested Redis SCAN batch size.

    Returns:
        Number of keys deleted.

    Raises:
        RedisError: When Redis scan or delete fails.
    """
    deleted_count = 0
    keys_to_delete: list[str] = []

    for redis_key in redis_client.scan_iter(
        match=key_pattern,
        count=scan_count,
    ):
        keys_to_delete.append(redis_key)
        if len(keys_to_delete) >= scan_count:
            deleted_count += redis_client.delete(*keys_to_delete)
            keys_to_delete.clear()

    if keys_to_delete:
        deleted_count += redis_client.delete(*keys_to_delete)

    return deleted_count


def create_redis_client(
    storage_uri: str,
    purpose: str,
    socket_timeout: float = DEFAULT_REDIS_SOCKET_TIMEOUT_SECONDS,
) -> Redis:
    """
    Create and verify a Redis client.

    Args:
        storage_uri: Redis storage URI.
        purpose: Human-readable use case for error messages.
        socket_timeout: Connection and read timeout in seconds.

    Returns:
        Connected Redis client.

    Raises:
        RuntimeError: When Redis cannot be initialized.
    """
    try:
        redis_client = Redis.from_url(
            storage_uri,
            decode_responses=True,
            socket_connect_timeout=socket_timeout,
            socket_timeout=socket_timeout,
        )
        redis_client.ping()
    except (RedisError, ValueError) as redis_error:
        raise RuntimeError(f"Unable to initialize Redis storage for {purpose}.") from redis_error
    return redis_client


def sha256_key_digest(value: str) -> str:
    """
    Hash a string into a hex digest for use in Redis key names.

    Keying on a SHA-256 digest keeps identifiers (usernames, user IDs)
    out of Redis keys so they are not exposed through key enumeration.

    Args:
        value: Already-normalized string to hash.

    Returns:
        SHA-256 hex digest of the value.

    Raises:
        None.
    """
    return core_hashing.sha256_hex(value)


def raise_storage_unavailable_as(
    error_cls: type[Exception],
    *,
    display_name: str,
    operation: str,
    err: RedisError,
) -> NoReturn:
    """
    Log a Redis outage and re-raise it as a domain-specific error.

    Wraps :func:`raise_redis_storage_unavailable` so each store can
    surface its own exception type (e.g. ``AuthSecurityStoreUnavailableError``)
    while sharing the sanitized logging and message format.

    Args:
        error_cls: Domain-specific exception class to raise.
        display_name: Human-readable storage purpose for logs and the
            raised message.
        operation: Storage operation that failed.
        err: Redis client exception.

    Raises:
        Exception: An instance of ``error_cls`` is always raised.
    """
    try:
        raise_redis_storage_unavailable(display_name, operation, err)
    except RedisStorageUnavailableError as store_err:
        raise error_cls(f"{display_name} is unavailable") from store_err


def select_storage_backend[StoreT](
    storage_uri: str,
    *,
    purpose: str,
    scheme_error_label: str,
    memory_factory: Callable[[], StoreT],
    redis_factory: Callable[[Redis], StoreT],
) -> StoreT:
    """
    Build a memory or Redis storage backend from a configured URI.

    Centralizes the ``memory://`` vs Redis dispatch shared by the auth
    security stores, MFA setup-secret store, and Garmin MFA code store.
    A blank URI is treated as ``memory://``.

    Args:
        storage_uri: Storage URI selecting the backend.
        purpose: Human-readable use case passed to
            :func:`create_redis_client` for error messages.
        scheme_error_label: Label used in the ``ValueError`` raised for
            an unsupported URI scheme (e.g.
            ``"AUTH_SECURITY_STORAGE_URI"``).
        memory_factory: Zero-argument factory for the in-memory backend.
        redis_factory: Factory taking a connected ``Redis`` client and
            returning the Redis-backed backend.

    Returns:
        The backend produced by the matching factory.

    Raises:
        RuntimeError: When Redis cannot be initialized.
        ValueError: When the storage URI scheme is unsupported.
    """
    normalized_uri = storage_uri.strip() or "memory://"
    if is_memory_storage_uri(normalized_uri):
        return memory_factory()
    if is_redis_storage_uri(normalized_uri):
        redis_client = create_redis_client(normalized_uri, purpose)
        return redis_factory(redis_client)

    storage_scheme = normalized_uri.split(":", 1)[0]
    raise ValueError(f"Unsupported {scheme_error_label} scheme: {storage_scheme or 'unknown'}")
