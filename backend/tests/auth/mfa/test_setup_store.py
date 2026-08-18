"""Tests for temporary MFA setup secret storage."""

import time
from fnmatch import fnmatch
from unittest.mock import patch

import pytest
from redis import RedisError

import auth.mfa.setup_store as auth_mfa_setup_store
import core.redis as core_redis


class FakeRedis:
    """Small Redis test double for MFA secret storage."""

    def __init__(self) -> None:
        """
        Initialize fake Redis state.

        Args:
            None.

        Returns:
            None.

        Raises:
            None.
        """
        self.values: dict[str, str] = {}
        self.expirations: dict[str, int] = {}

    def set(self, key: str, value: str, ex: int | None = None) -> None:
        """
        Set a fake Redis key.

        Args:
            key: Redis key.
            value: Redis value.
            ex: Optional TTL in seconds.

        Returns:
            None.

        Raises:
            None.
        """
        self.values[key] = value
        if ex is not None:
            self.expirations[key] = ex

    def get(self, key: str) -> str | None:
        """
        Get a fake Redis key.

        Args:
            key: Redis key.

        Returns:
            Stored value, or None.

        Raises:
            None.
        """
        return self.values.get(key)

    def delete(self, *keys: str) -> int:
        """
        Delete fake Redis keys.

        Args:
            keys: Redis keys to delete.

        Returns:
            Number of deleted keys.

        Raises:
            None.
        """
        deleted_count = 0
        for key in keys:
            if key in self.values:
                deleted_count += 1
            self.values.pop(key, None)
            self.expirations.pop(key, None)
        return deleted_count

    def scan_iter(self, match: str | None = None, count: int | None = None):
        """
        Iterate fake Redis keys matching a glob pattern.

        Args:
            match: Optional glob pattern.
            count: Optional scan batch size.

        Returns:
            Iterator of matching keys.

        Raises:
            None.
        """
        del count
        for key in list(self.values):
            if match is None or fnmatch(key, match):
                yield key


class FailingRedis(FakeRedis):
    """Redis test double that raises for one operation."""

    def __init__(self, failing_operation: str) -> None:
        """
        Initialize the failing fake Redis client.

        Args:
            failing_operation: Redis operation that should fail.

        Returns:
            None.

        Raises:
            None.
        """
        super().__init__()
        self.failing_operation = failing_operation

    def _fail_if_needed(self, operation: str) -> None:
        """
        Raise RedisError for the configured operation.

        Args:
            operation: Operation currently being executed.

        Returns:
            None.

        Raises:
            RedisError: When operation matches the configured failure.
        """
        if self.failing_operation == operation:
            raise RedisError("redis unavailable")

    def set(self, key: str, value: str, ex: int | None = None) -> None:
        """
        Set a key or raise RedisError.

        Args:
            key: Redis key.
            value: Redis value.
            ex: Optional TTL in seconds.

        Returns:
            None.

        Raises:
            RedisError: When set is configured to fail.
        """
        self._fail_if_needed("set")
        return super().set(key, value, ex)

    def get(self, key: str) -> str | None:
        """
        Get a key or raise RedisError.

        Args:
            key: Redis key.

        Returns:
            Stored value, or None.

        Raises:
            RedisError: When get is configured to fail.
        """
        self._fail_if_needed("get")
        return super().get(key)

    def delete(self, *keys: str) -> int:
        """
        Delete keys or raise RedisError.

        Args:
            keys: Redis keys to delete.

        Returns:
            Number of deleted keys.

        Raises:
            RedisError: When delete is configured to fail.
        """
        self._fail_if_needed("delete")
        return super().delete(*keys)

    def scan_iter(self, match: str | None = None, count: int | None = None):
        """
        Iterate keys or raise RedisError.

        Args:
            match: Optional glob pattern.
            count: Optional scan batch size.

        Returns:
            Iterator of matching keys.

        Raises:
            RedisError: When scan_iter is configured to fail.
        """
        self._fail_if_needed("scan_iter")
        yield from super().scan_iter(match, count)


class TestMFASecretStore:
    """Tests for the in-memory MFA secret store."""

    def test_memory_store_lifecycle(self) -> None:
        """Test basic store, retrieve, and delete lifecycle."""
        store = auth_mfa_setup_store.MFASecretStore()

        store.add_secret(123, "secret-value")
        assert store.get_secret(123) == "secret-value"
        assert store.has_secret(123) is True

        store.delete_secret(123)
        assert store.get_secret(123) is None
        assert store.has_secret(123) is False

    def test_add_secret_encryption_failure(self) -> None:
        """Test ValueError raised when encryption returns None."""
        with (
            patch("auth.mfa.setup_store.core_cryptography.encrypt_token_fernet", return_value=None),
            pytest.raises(ValueError, match="Failed to encrypt MFA secret"),
        ):
            auth_mfa_setup_store.MFASecretStore().add_secret(123, "secret-value")

    def test_has_secret_expired_after_add(self) -> None:
        """Test has_secret returns False for expired secret."""
        store = auth_mfa_setup_store.MFASecretStore()
        store.add_secret(123, "secret-value")
        store._store[123]["expires_at"] = time.time() - 1
        assert store.has_secret(123) is False

    def test_clear_all_happy_path(self) -> None:
        """Test clear_all removes all secrets."""
        store = auth_mfa_setup_store.MFASecretStore()
        store.add_secret(123, "secret-value")
        store.add_secret(456, "other-secret")
        store.clear_all()
        assert store.get_secret(123) is None
        assert store.get_secret(456) is None
        assert store.has_secret(123) is False

    def test_get_stats_with_secrets(self) -> None:
        """Test get_stats returns correct counts."""
        store = auth_mfa_setup_store.MFASecretStore()
        store.add_secret(123, "secret-value")
        stats = store.get_stats()
        assert stats["total_secrets"] >= 1
        assert stats["active_secrets"] >= 1
        assert stats["ttl_seconds"] >= 0

    def test_encrypt_secret_error(self) -> None:
        """Test _encrypt_secret raises ValueError when encryption returns None."""
        with (
            patch("auth.mfa.setup_store.core_cryptography.encrypt_token_fernet", return_value=None),
            pytest.raises(ValueError, match="Failed to encrypt MFA secret"),
        ):
            auth_mfa_setup_store._encrypt_secret("test-secret")

    def test_decrypt_secret_returns_none_on_error(self) -> None:
        """Test _decrypt_secret returns None when decryption fails."""
        with patch("auth.mfa.setup_store.core_cryptography.decrypt_token_fernet", side_effect=Exception("bad decrypt")):
            result = auth_mfa_setup_store._decrypt_secret("bad-encrypted-data", 123)
            assert result is None

    def test_memory_store_expired_secret_is_evicted(self) -> None:
        """Test memory store evicts expired secrets on read."""
        store = auth_mfa_setup_store.MFASecretStore(ttl_seconds=-1)
        store.add_secret(123, "secret-value")

        assert store.get_secret(123) is None
        assert store.has_secret(123) is False


class TestRedisMFASecretStore:
    """Tests for Redis-backed MFA secret storage."""

    def test_redis_store_lifecycle(self) -> None:
        """Test Redis store add, get, has, and delete."""
        redis_client = FakeRedis()
        store = auth_mfa_setup_store.RedisMFASecretStore(
            redis_client,
            ttl_seconds=42,
        )

        store.add_secret(123, "secret-value")
        redis_key = store._secret_key(123)

        assert redis_client.values[redis_key] != "secret-value"
        assert redis_client.expirations[redis_key] == 42
        assert store.has_secret(123) is True
        assert store.get_secret(123) == "secret-value"

        store.delete_secret(123)

        assert store.has_secret(123) is False
        assert store.get_secret(123) is None

    def test_redis_key_hashes_user_id(self) -> None:
        """Test Redis store does not write raw user IDs in key names."""
        redis_client = FakeRedis()
        store = auth_mfa_setup_store.RedisMFASecretStore(redis_client)

        store.add_secret(42, "secret-value")
        redis_key = next(iter(redis_client.values))

        assert redis_key.startswith("endurain:auth:mfa:setup_secret:")
        assert not redis_key.endswith(":42")

    def test_redis_store_clear_all(self) -> None:
        """Test Redis store clears all setup secret keys."""
        redis_client = FakeRedis()
        store = auth_mfa_setup_store.RedisMFASecretStore(redis_client)
        unrelated_key = "endurain:auth:mfa:pending:other"

        store.add_secret(1, "secret-one")
        store.add_secret(2, "secret-two")
        redis_client.set(unrelated_key, "kept")

        store.clear_all()

        assert redis_client.values == {unrelated_key: "kept"}

    def test_redis_get_failure_is_sanitized(self) -> None:
        """Test Redis get errors become MFA-store outage errors."""
        store = auth_mfa_setup_store.RedisMFASecretStore(FailingRedis("get"))

        with pytest.raises(auth_mfa_setup_store.MFASecretStoreUnavailableError) as exc_info:
            store.get_secret(123)

        assert isinstance(
            exc_info.value.__cause__,
            core_redis.RedisStorageUnavailableError,
        )

    def test_redis_set_failure_is_sanitized(self) -> None:
        """Test Redis set errors become MFA-store outage errors."""
        store = auth_mfa_setup_store.RedisMFASecretStore(FailingRedis("set"))

        with pytest.raises(auth_mfa_setup_store.MFASecretStoreUnavailableError):
            store.add_secret(123, "secret-value")


class TestMFASecretStoreFactory:
    """Tests for MFA secret store factory helpers."""

    def test_create_mfa_secret_store_memory_uri(self) -> None:
        """Test memory URI creates memory-backed storage."""
        store = auth_mfa_setup_store.create_mfa_secret_store("memory://")

        assert isinstance(store, auth_mfa_setup_store.MFASecretStore)

    def test_create_mfa_secret_store_blank_uri(self) -> None:
        """Test blank URI creates memory-backed storage."""
        store = auth_mfa_setup_store.create_mfa_secret_store("")

        assert isinstance(store, auth_mfa_setup_store.MFASecretStore)

    def test_create_mfa_secret_store_redis_uri(self, monkeypatch) -> None:
        """Test Redis URI creates Redis-backed storage."""
        monkeypatch.setattr(
            auth_mfa_setup_store.core_redis,
            "create_redis_client",
            lambda storage_uri, purpose: FakeRedis(),
        )

        store = auth_mfa_setup_store.create_mfa_secret_store("redis://localhost:6379/0")

        assert isinstance(store, auth_mfa_setup_store.RedisMFASecretStore)

    def test_create_mfa_secret_store_rejects_unknown_uri(self) -> None:
        """Test unsupported storage URIs are rejected."""
        with pytest.raises(ValueError) as exc_info:
            auth_mfa_setup_store.create_mfa_secret_store("postgresql://localhost/db")

        assert "Unsupported MFA secret storage URI" in str(exc_info.value)

    def test_mfa_secret_uri_falls_back_to_rate_limit(
        self,
        monkeypatch,
    ) -> None:
        """Test MFA secret URI falls back to rate limit URI."""
        monkeypatch.setattr(
            auth_mfa_setup_store.core_config.settings,
            "AUTH_SECURITY_STORAGE_URI",
            None,
        )
        monkeypatch.setattr(
            auth_mfa_setup_store.core_config.settings,
            "RATE_LIMIT_STORAGE_URI",
            "redis://localhost:6379/0",
        )

        assert auth_mfa_setup_store.get_mfa_secret_storage_uri() == "redis://localhost:6379/0"

    def test_mfa_secret_uri_prefers_auth_specific_uri(
        self,
        monkeypatch,
    ) -> None:
        """Test auth-specific URI overrides the rate limit URI."""
        monkeypatch.setattr(
            auth_mfa_setup_store.core_config.settings,
            "AUTH_SECURITY_STORAGE_URI",
            "memory://",
        )
        monkeypatch.setattr(
            auth_mfa_setup_store.core_config.settings,
            "RATE_LIMIT_STORAGE_URI",
            "redis://localhost:6379/0",
        )

        assert auth_mfa_setup_store.get_mfa_secret_storage_uri() == "memory://"


class TestMFASecretStoreCleanup:
    """Tests for the MFA secret store cleanup thread."""

    def test_cleanup_expired_secrets_removes_expired(self, monkeypatch) -> None:
        """Expired secrets are removed by the cleanup loop body."""
        store = auth_mfa_setup_store.MFASecretStore()
        store.add_secret(123, "secret-value")
        store._store[123]["expires_at"] = time.time() - 1

        sleeps: list[float] = []

        def mock_sleep(seconds: float) -> None:
            sleeps.append(seconds)
            raise StopIteration("break")

        monkeypatch.setattr(time, "sleep", mock_sleep)

        with pytest.raises(StopIteration):
            store._cleanup_expired_secrets()

        assert 123 not in store._store

    def test_cleanup_expired_secrets_no_expired(self, monkeypatch) -> None:
        """Non-expired secrets are preserved by the cleanup loop body."""
        store = auth_mfa_setup_store.MFASecretStore()
        store.add_secret(123, "secret-value")

        sleeps: list[float] = []

        def mock_sleep(seconds: float) -> None:
            sleeps.append(seconds)
            raise StopIteration("break")

        monkeypatch.setattr(time, "sleep", mock_sleep)

        with pytest.raises(StopIteration):
            store._cleanup_expired_secrets()

        assert 123 in store._store

    def test_cleanup_expired_secrets_error_handling(self, monkeypatch) -> None:
        """Exceptions in the cleanup loop are caught and logged."""
        store = auth_mfa_setup_store.MFASecretStore()
        store.add_secret(123, "secret-value")

        class FailingDict(dict):  # type: ignore[type-arg]
            def items(self) -> list:  # type: ignore[override]
                raise Exception("cleanup failed")

        store._store = FailingDict(store._store)

        sleeps: list[float] = []

        def mock_sleep(seconds: float) -> None:
            sleeps.append(seconds)
            raise StopIteration("break")

        monkeypatch.setattr(time, "sleep", mock_sleep)

        with pytest.raises(StopIteration):
            store._cleanup_expired_secrets()

        assert sleeps == [60]


class TestMFASecretStoreErrorHandling:
    """Tests for error handling in memory store methods."""

    def test_get_secret_logs_error_on_exception(self) -> None:
        """get_secret returns None and logs when decryption fails."""
        store = auth_mfa_setup_store.MFASecretStore()
        store.add_secret(123, "secret-value")
        with patch("auth.mfa.setup_store._decrypt_secret", side_effect=Exception("decrypt failed")):
            result = store.get_secret(123)
            assert result is None

    def test_delete_secret_logs_error_on_exception(self) -> None:
        """delete_secret catches and logs exception from store access."""

        class FailingDict(dict):  # type: ignore[type-arg]
            def __contains__(self, key: object) -> bool:
                raise Exception("test error")

        store = auth_mfa_setup_store.MFASecretStore()
        store._store = FailingDict(store._store)
        store.delete_secret(123)

    def test_has_secret_logs_error_on_exception(self) -> None:
        """has_secret returns False when store access raises."""

        class FailingDict(dict):  # type: ignore[type-arg]
            def __contains__(self, key: object) -> bool:
                raise Exception("test error")

        store = auth_mfa_setup_store.MFASecretStore()
        store._store = FailingDict(store._store)
        result = store.has_secret(123)
        assert result is False

    def test_clear_all_logs_error_on_exception(self) -> None:
        """clear_all catches and logs exception from store clear."""

        class FailingDict(dict):  # type: ignore[type-arg]
            def clear(self) -> None:
                raise Exception("test error")

        store = auth_mfa_setup_store.MFASecretStore()
        store._store = FailingDict(store._store)
        store.clear_all()

    def test_get_stats_logs_error_on_exception(self) -> None:
        """get_stats returns error dict when store access raises."""

        class FailingDict(dict):  # type: ignore[type-arg]
            def values(self) -> object:  # type: ignore[override]
                raise Exception("test error")

        store = auth_mfa_setup_store.MFASecretStore()
        store._store = FailingDict(store._store)
        stats = store.get_stats()
        assert "error" in stats


class TestRedisMFASecretStoreEdgeCases:
    """Edge-case tests for Redis-backed MFA secret storage."""

    def test_redis_delete_failure_logged(self) -> None:
        """Redis delete errors are logged (not re-raised)."""
        store = auth_mfa_setup_store.RedisMFASecretStore(FailingRedis("delete"))
        store.delete_secret(123)

    def test_redis_has_secret_failure_is_sanitized(self) -> None:
        """Redis has_secret errors become MFA-store outage errors."""
        store = auth_mfa_setup_store.RedisMFASecretStore(FailingRedis("get"))
        with pytest.raises(auth_mfa_setup_store.MFASecretStoreUnavailableError):
            store.has_secret(123)

    def test_redis_clear_all_failure_is_sanitized(self) -> None:
        """Redis clear_all errors become MFA-store outage errors."""
        store = auth_mfa_setup_store.RedisMFASecretStore(FailingRedis("scan_iter"))
        with pytest.raises(auth_mfa_setup_store.MFASecretStoreUnavailableError):
            store.clear_all()

    def test_redis_get_stats(self) -> None:
        """Redis get_stats returns correct counts."""
        redis_client = FakeRedis()
        store = auth_mfa_setup_store.RedisMFASecretStore(redis_client, ttl_seconds=300)
        store.add_secret(123, "secret-one")
        store.add_secret(456, "secret-two")
        stats = store.get_stats()
        assert stats["total_secrets"] == 2
        assert stats["active_secrets"] == 2
        assert stats["expired_secrets"] == 0
        assert stats["ttl_seconds"] == 300

    def test_redis_get_stats_failure(self) -> None:
        """Redis get_stats returns error dict on scan failure."""
        store = auth_mfa_setup_store.RedisMFASecretStore(FailingRedis("scan_iter"))
        stats = store.get_stats()
        assert stats["error"] == "MFASecretStoreUnavailableError"


class TestMFASecretStoreModuleLevel:
    """Tests for module-level helpers."""

    def test_get_mfa_secret_store(self) -> None:
        """get_mfa_secret_store returns the module-level instance."""
        store = auth_mfa_setup_store.get_mfa_secret_store()
        assert isinstance(store, (auth_mfa_setup_store.MFASecretStore, auth_mfa_setup_store.RedisMFASecretStore))

    def test_get_mfa_secret_storage_uri_fallback_memory(self, monkeypatch) -> None:
        """When both storage URIs are unset, memory:// is returned."""
        monkeypatch.setattr(auth_mfa_setup_store.core_config.settings, "AUTH_SECURITY_STORAGE_URI", None)
        monkeypatch.setattr(auth_mfa_setup_store.core_config.settings, "RATE_LIMIT_STORAGE_URI", None)
        assert auth_mfa_setup_store.get_mfa_secret_storage_uri() == "memory://"
