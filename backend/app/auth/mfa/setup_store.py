"""Temporary MFA setup secret storage with TTL."""

import threading
import time
from typing import NoReturn

from redis import Redis, RedisError

import core.config as core_config
import core.cryptography as core_cryptography
import core.logger as core_logger
import core.redis as core_redis

_REDIS_MFA_SECRET_KEY_PREFIX = "endurain:auth:mfa:setup_secret"  # noqa: S105 - Redis key prefix, not a credential


class MFASecretStoreUnavailableError(RuntimeError):
    """
    Raised when MFA secret storage cannot be reached.

    Attributes:
        None.
    """


def _raise_store_unavailable(operation: str, err: RedisError) -> NoReturn:
    """
    Raise a sanitized MFA secret storage exception.

    Args:
        operation: Storage operation that failed.
        err: Redis client exception.

    Raises:
        MFASecretStoreUnavailableError: Always raised.
    """
    core_redis.raise_storage_unavailable_as(
        MFASecretStoreUnavailableError,
        display_name="MFA secret storage",
        operation=operation,
        err=err,
    )


def get_mfa_secret_storage_uri() -> str:
    """
    Resolve the configured MFA secret storage URI.

    Returns:
        Explicit auth security URI, or the rate-limit URI when unset.

    Raises:
        None.
    """
    return core_config.settings.resolved_auth_security_storage_uri


class MFASecretStore:
    """
    Thread-safe storage for temporary MFA secrets with TTL.

    Attributes:
        _store: Internal storage for encrypted secrets.
        _lock: Thread synchronization lock.
        _ttl_seconds: Time-to-live for stored secrets.
        _cleanup_thread: Background thread for cleanup.
    """

    DEFAULT_TTL_SECONDS: int = 300

    def __init__(self, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> None:
        """
        Initialize the MFA secret store.

        Args:
            ttl_seconds: Time-to-live for secrets in seconds.
        """
        self._store: dict[int, dict[str, str | float]] = {}
        self._lock = threading.RLock()
        self._ttl_seconds = ttl_seconds
        self._cleanup_thread: threading.Thread | None = None
        self._start_cleanup_thread()

    def _start_cleanup_thread(self) -> None:
        """
        Start the background cleanup thread if not running.

        Returns:
            None.

        Raises:
            None.
        """
        if self._cleanup_thread is None or not self._cleanup_thread.is_alive():
            self._cleanup_thread = threading.Thread(
                target=self._cleanup_expired_secrets,
                daemon=True,
                name="MFA-Secret-Cleanup",
            )
            self._cleanup_thread.start()

    def _cleanup_expired_secrets(self) -> None:
        """
        Continuously remove expired secrets from storage.

        Returns:
            None.

        Raises:
            None.
        """
        while True:
            try:
                current_time = time.time()
                with self._lock:
                    expired_users = [
                        user_id for user_id, data in self._store.items() if current_time > data["expires_at"]
                    ]
                    for user_id in expired_users:
                        del self._store[user_id]
                        core_logger.print_to_log(
                            f"Cleaned up expired MFA secret for user {user_id}",
                            "debug",
                        )

                time.sleep(30)
            except Exception as err:
                core_logger.print_to_log(
                    f"Error in MFA secret cleanup thread: {type(err).__name__}",
                    "error",
                    exc=err,
                )
                time.sleep(60)

    def add_secret(self, user_id: int, secret: str) -> None:
        """
        Store an encrypted MFA secret with expiration.

        Args:
            user_id: The user ID to associate with the secret.
            secret: The plaintext MFA secret to encrypt and store.

        Raises:
            ValueError: If encryption fails.
            Exception: If storage operation fails.
        """
        try:
            encrypted_secret = core_cryptography.encrypt_token_fernet(secret)
            if not encrypted_secret:
                raise ValueError("Failed to encrypt MFA secret")

            expires_at = time.time() + self._ttl_seconds

            with self._lock:
                self._store[user_id] = {
                    "encrypted_secret": encrypted_secret,
                    "expires_at": expires_at,
                }

            _log_secret_stored(user_id, self._ttl_seconds)
        except Exception as err:
            core_logger.print_to_log(
                f"Failed to add MFA secret for user {user_id}: {type(err).__name__}",
                "error",
                exc=err,
            )
            raise

    def get_secret(self, user_id: int) -> str | None:
        """
        Retrieve and decrypt an MFA secret if not expired.

        Args:
            user_id: The user ID to retrieve the secret for.

        Returns:
            The decrypted MFA secret, or None if not found or
            expired.
        """
        try:
            with self._lock:
                if user_id not in self._store:
                    return None

                data = self._store[user_id]

                # Check if expired
                if time.time() > data["expires_at"]:
                    del self._store[user_id]
                    core_logger.print_to_log(f"MFA secret expired for user {user_id}", "debug")
                    return None

                # Decrypt and return
                encrypted_secret = str(data["encrypted_secret"])
                decrypted_secret = _decrypt_secret(encrypted_secret, user_id)
                return decrypted_secret

        except Exception as err:
            core_logger.print_to_log(
                f"Failed to get MFA secret for user {user_id}: {type(err).__name__}",
                "error",
                exc=err,
            )
            return None

    def delete_secret(self, user_id: int) -> None:
        """
        Remove an MFA secret from storage.

        Args:
            user_id: The user ID whose secret to delete.
        """
        try:
            with self._lock:
                if user_id in self._store:
                    del self._store[user_id]
                    core_logger.print_to_log(
                        f"Securely deleted MFA secret for user {user_id}",
                        "debug",
                    )
        except Exception as err:
            core_logger.print_to_log(
                f"Failed to delete MFA secret for user {user_id}: {type(err).__name__}",
                "error",
                exc=err,
            )

    def has_secret(self, user_id: int) -> bool:
        """
        Check if a non-expired secret exists for a user.

        Args:
            user_id: The user ID to check.

        Returns:
            True if a valid secret exists, False otherwise.
        """
        try:
            with self._lock:
                if user_id not in self._store:
                    return False

                # Check if expired
                if time.time() > self._store[user_id]["expires_at"]:
                    del self._store[user_id]
                    return False

                return True
        except Exception as err:
            core_logger.print_to_log(
                f"Failed to check MFA secret for user {user_id}: {type(err).__name__}",
                "error",
                exc=err,
            )
            return False

    def clear_all(self) -> None:
        """
        Remove all MFA secrets from storage.

        Returns:
            None.
        """
        try:
            with self._lock:
                cleared_count = len(self._store)
                self._store.clear()
                core_logger.print_to_log(f"Cleared {cleared_count} MFA secrets from store", "info")
        except Exception as err:
            core_logger.print_to_log(
                f"Failed to clear MFA secret store: {type(err).__name__}",
                "error",
                exc=err,
            )

    def get_stats(self) -> dict[str, int] | dict[str, str]:
        """
        Get statistics about the secret store.

        Returns:
            Dictionary with total, expired, and active secret
            counts.
        """
        try:
            with self._lock:
                current_time = time.time()
                total_count = len(self._store)
                expired_count = sum(1 for data in self._store.values() if current_time > data["expires_at"])

                return {
                    "total_secrets": total_count,
                    "expired_secrets": expired_count,
                    "active_secrets": total_count - expired_count,
                    "ttl_seconds": self._ttl_seconds,
                }
        except Exception as err:
            core_logger.print_to_log(
                f"Failed to get MFA secret store stats: {type(err).__name__}",
                "error",
                exc=err,
            )
            return {"error": type(err).__name__}

    def __repr__(self) -> str:
        """
        Return a string representation of the store.

        Returns:
            String showing active secrets and TTL.
        """
        stats = self.get_stats()
        active_secrets = stats.get("active_secrets", 0)
        return f"MFASecretStore(active={active_secrets}, ttl={self._ttl_seconds}s)"


def _user_id_digest(user_id: int) -> str:
    """
    Hash a user ID for Redis key names.

    Args:
        user_id: User ID to hash.

    Returns:
        SHA-256 digest for use in Redis keys.

    Raises:
        None.
    """
    return core_redis.sha256_key_digest(str(user_id))


def _encrypt_secret(secret: str) -> str:
    """
    Encrypt a plaintext MFA secret.

    Args:
        secret: Plaintext MFA setup secret.

    Returns:
        Fernet-encrypted secret.

    Raises:
        ValueError: When encryption returns no value.
        HTTPException: When Fernet encryption fails.
    """
    encrypted_secret = core_cryptography.encrypt_token_fernet(secret)
    if not encrypted_secret:
        raise ValueError("Failed to encrypt MFA secret")
    return encrypted_secret


def _decrypt_secret(encrypted_secret: str, user_id: int) -> str | None:
    """
    Decrypt an encrypted MFA secret.

    Args:
        encrypted_secret: Fernet-encrypted MFA setup secret.
        user_id: User ID used for sanitized logging.

    Returns:
        Decrypted MFA setup secret, or None on failure.

    Raises:
        None.
    """
    try:
        return core_cryptography.decrypt_token_fernet(encrypted_secret)
    except Exception as err:
        core_logger.print_to_log(
            f"Failed to decrypt MFA secret for user {user_id}: {type(err).__name__}",
            "error",
            exc=err,
        )
        return None


def _log_secret_stored(user_id: int, ttl_seconds: int) -> None:
    """
    Log MFA secret storage without exposing the secret.

    Args:
        user_id: User ID associated with the setup secret.
        ttl_seconds: Secret time-to-live in seconds.

    Returns:
        None.

    Raises:
        None.
    """
    core_logger.print_to_log(
        f"Securely stored MFA secret for user {user_id} (expires in {ttl_seconds}s)",
        "debug",
    )


class RedisMFASecretStore:
    """
    Store temporary MFA setup secrets in Redis.

    Attributes:
        _redis: Redis client used for storage.
        _ttl_seconds: Time-to-live for stored secrets.
    """

    def __init__(
        self,
        redis_client: Redis,
        ttl_seconds: int = MFASecretStore.DEFAULT_TTL_SECONDS,
    ) -> None:
        """
        Initialize the Redis MFA secret store.

        Args:
            redis_client: Redis client used for storage.
            ttl_seconds: Time-to-live for secrets in seconds.
        """
        self._redis = redis_client
        self._ttl_seconds = ttl_seconds

    def _secret_key(self, user_id: int) -> str:
        """
        Build the Redis key for a pending MFA setup secret.

        Args:
            user_id: User ID associated with the setup secret.

        Returns:
            Redis key for the encrypted secret.

        Raises:
            None.
        """
        return f"{_REDIS_MFA_SECRET_KEY_PREFIX}:{_user_id_digest(user_id)}"

    def add_secret(self, user_id: int, secret: str) -> None:
        """
        Store an encrypted MFA secret with Redis expiration.

        Args:
            user_id: User ID to associate with the secret.
            secret: Plaintext MFA secret to encrypt and store.

        Returns:
            None.

        Raises:
            MFASecretStoreUnavailableError: When Redis access fails.
            ValueError: If encryption fails.
            HTTPException: If Fernet encryption fails.
        """
        encrypted_secret = _encrypt_secret(secret)
        try:
            self._redis.set(
                self._secret_key(user_id),
                encrypted_secret,
                ex=self._ttl_seconds,
            )
        except RedisError as err:
            _raise_store_unavailable("add MFA setup secret", err)
        _log_secret_stored(user_id, self._ttl_seconds)

    def get_secret(self, user_id: int) -> str | None:
        """
        Retrieve and decrypt an MFA secret if present.

        Args:
            user_id: User ID to retrieve the secret for.

        Returns:
            Decrypted MFA secret, or None when missing or invalid.

        Raises:
            MFASecretStoreUnavailableError: When Redis access fails.
        """
        try:
            encrypted_secret = self._redis.get(self._secret_key(user_id))
        except RedisError as err:
            _raise_store_unavailable("get MFA setup secret", err)

        if encrypted_secret is None:
            return None
        return _decrypt_secret(str(encrypted_secret), user_id)

    def delete_secret(self, user_id: int) -> None:
        """
        Remove an MFA secret from Redis storage.

        Args:
            user_id: User ID whose secret should be removed.

        Returns:
            None.
        """
        try:
            self._redis.delete(self._secret_key(user_id))
        except RedisError as err:
            core_logger.print_to_log(
                "Failed to delete MFA setup secret from Redis; entry will expire naturally via TTL",
                "warning",
                exc=err,
            )

    def has_secret(self, user_id: int) -> bool:
        """
        Check if a non-expired secret exists for a user.

        Args:
            user_id: User ID to check.

        Returns:
            True if a secret exists, False otherwise.

        Raises:
            MFASecretStoreUnavailableError: When Redis access fails.
        """
        try:
            return self._redis.get(self._secret_key(user_id)) is not None
        except RedisError as err:
            _raise_store_unavailable("check MFA setup secret", err)

    def clear_all(self) -> None:
        """
        Remove all MFA setup secrets from Redis storage.

        Returns:
            None.

        Raises:
            MFASecretStoreUnavailableError: When Redis access fails.
        """
        key_pattern = f"{_REDIS_MFA_SECRET_KEY_PREFIX}:*"
        try:
            core_redis.delete_matching_keys(self._redis, key_pattern)
        except RedisError as err:
            _raise_store_unavailable("clear MFA setup secrets", err)

    def get_stats(self) -> dict[str, int] | dict[str, str]:
        """
        Get statistics about the Redis secret store.

        Returns:
            Dictionary with total, expired, and active secret counts.
        """
        key_pattern = f"{_REDIS_MFA_SECRET_KEY_PREFIX}:*"
        try:
            total_count = sum(
                1
                for _redis_key in self._redis.scan_iter(
                    match=key_pattern,
                    count=100,
                )
            )
        except RedisError as err:
            core_logger.print_to_log(
                "Failed to get MFA secret store stats from Redis",
                "error",
                exc=err,
            )
            return {"error": "MFASecretStoreUnavailableError"}
        return {
            "total_secrets": total_count,
            "expired_secrets": 0,
            "active_secrets": total_count,
            "ttl_seconds": self._ttl_seconds,
        }

    def __repr__(self) -> str:
        """
        Return a string representation of the store.

        Returns:
            String showing active secrets and TTL.
        """
        stats = self.get_stats()
        active_secrets = stats.get("active_secrets", 0)
        return f"RedisMFASecretStore(active={active_secrets}, ttl={self._ttl_seconds}s)"


MFASecretStoreBackend = MFASecretStore | RedisMFASecretStore


def create_mfa_secret_store(
    storage_uri: str,
) -> MFASecretStoreBackend:
    """
    Create an MFA secret store for the configured backend.

    Args:
        storage_uri: Storage URI selecting memory or Redis.

    Returns:
        MFA setup secret store instance.

    Raises:
        RuntimeError: When Redis cannot be initialized.
        ValueError: When the storage URI scheme is unsupported.
    """
    return core_redis.select_storage_backend(
        storage_uri,
        purpose="MFA secret storage",
        scheme_error_label="MFA secret storage URI",
        memory_factory=MFASecretStore,
        redis_factory=RedisMFASecretStore,
    )


def get_mfa_secret_store() -> MFASecretStoreBackend:
    """
    Get the module-level MFA secret store instance.

    Returns:
        The global MFA secret store instance.

    Raises:
        None.
    """
    return mfa_secret_store


mfa_secret_store = create_mfa_secret_store(get_mfa_secret_storage_uri())
