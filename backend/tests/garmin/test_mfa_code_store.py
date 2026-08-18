"""Tests for garmin.mfa_code_store."""

import time
from unittest.mock import MagicMock, patch

import pytest
from redis import RedisError

import garmin.mfa_code_store as mfa_code_store


class TestGarminMFACodeStore:
    """GarminMFACodeStore: in-memory TTL-backed store."""

    def _make_store(self, ttl: int = 90) -> mfa_code_store.GarminMFACodeStore:
        return mfa_code_store.GarminMFACodeStore(ttl_seconds=ttl)

    def test_add_and_has_code(self):
        store = self._make_store()
        store.add_code(1, "123456")
        assert store.has_code(1) is True

    def test_get_code_returns_value(self):
        store = self._make_store()
        store.add_code(2, "654321")
        assert store.get_code(2) == "654321"

    def test_get_code_missing_returns_none(self):
        store = self._make_store()
        assert store.get_code(99) is None

    def test_has_code_missing_returns_false(self):
        store = self._make_store()
        assert store.has_code(99) is False

    def test_delete_code_removes_entry(self):
        store = self._make_store()
        store.add_code(3, "abc")
        store.delete_code(3)
        assert store.has_code(3) is False
        assert store.get_code(3) is None

    def test_delete_code_missing_is_noop(self):
        store = self._make_store()
        store.delete_code(99)  # Should not raise

    def test_clear_all_empties_store(self):
        store = self._make_store()
        store.add_code(1, "111")
        store.add_code(2, "222")
        store.clear_all()
        assert store.has_code(1) is False
        assert store.has_code(2) is False

    def test_expired_entry_has_code_returns_false(self):
        store = self._make_store(ttl=1)
        store.add_code(5, "999")
        # Force expiration by patching time
        with patch("garmin.mfa_code_store.time") as mock_time:
            mock_time.time.return_value = time.time() + 200
            assert store.has_code(5) is False

    def test_expired_entry_get_code_returns_none(self):
        store = self._make_store(ttl=1)
        store.add_code(6, "777")
        with patch("garmin.mfa_code_store.time") as mock_time:
            mock_time.time.return_value = time.time() + 200
            assert store.get_code(6) is None

    def test_overwrite_code_updates_value(self):
        store = self._make_store()
        store.add_code(7, "old")
        store.add_code(7, "new")
        assert store.get_code(7) == "new"

    def test_repr_contains_active_count(self):
        store = self._make_store()
        store.add_code(1, "x")
        assert "active=1" in repr(store)


class TestRedisGarminMFACodeStore:
    """RedisGarminMFACodeStore: Redis-backed store."""

    def _make_store(self, redis=None) -> mfa_code_store.RedisGarminMFACodeStore:
        if redis is None:
            redis = MagicMock()
        return mfa_code_store.RedisGarminMFACodeStore(redis_client=redis, ttl_seconds=90)

    def test_add_code_calls_set_with_ttl(self):
        redis = MagicMock()
        store = self._make_store(redis)
        store.add_code(1, "123456")
        redis.set.assert_called_once()
        call_kwargs = redis.set.call_args
        assert call_kwargs.kwargs.get("ex") == 90 or (len(call_kwargs.args) > 2 and call_kwargs.args[2] == 90)

    def test_get_code_decodes_bytes(self):
        redis = MagicMock()
        redis.get.return_value = b"654321"
        store = self._make_store(redis)
        assert store.get_code(2) == "654321"

    def test_get_code_none_when_missing(self):
        redis = MagicMock()
        redis.get.return_value = None
        store = self._make_store(redis)
        assert store.get_code(99) is None

    def test_has_code_true_when_present(self):
        redis = MagicMock()
        redis.get.return_value = b"code"
        store = self._make_store(redis)
        assert store.has_code(1) is True

    def test_has_code_false_when_missing(self):
        redis = MagicMock()
        redis.get.return_value = None
        store = self._make_store(redis)
        assert store.has_code(1) is False

    def test_delete_code_calls_redis_delete(self):
        redis = MagicMock()
        store = self._make_store(redis)
        store.delete_code(3)
        redis.delete.assert_called_once()

    def test_delete_code_redis_error_is_logged_not_raised(self):
        redis = MagicMock()
        redis.delete.side_effect = RedisError("conn error")
        store = self._make_store(redis)
        with patch("garmin.mfa_code_store.core_logger.print_to_log") as mock_log:
            store.delete_code(3)  # Should not raise
        mock_log.assert_called()

    def test_add_code_redis_error_raises_unavailable(self):
        redis = MagicMock()
        redis.set.side_effect = RedisError("conn error")
        store = self._make_store(redis)
        with (
            patch("garmin.mfa_code_store.core_redis.raise_redis_storage_unavailable") as mock_raise,
            patch(
                "garmin.mfa_code_store.core_redis.RedisStorageUnavailableError",
                mfa_code_store.GarminMFACodeStoreUnavailableError,
            ),
        ):
            mock_raise.side_effect = mfa_code_store.GarminMFACodeStoreUnavailableError("unavailable")
            with pytest.raises(mfa_code_store.GarminMFACodeStoreUnavailableError):
                store.add_code(1, "x")

    def test_repr_contains_ttl(self):
        store = self._make_store()
        assert "90" in repr(store)


class TestCreateGarminMFACodeStore:
    """create_garmin_mfa_code_store factory: selects correct backend."""

    def test_memory_uri_returns_in_memory_store(self):
        store = mfa_code_store.create_garmin_mfa_code_store("memory://")
        assert isinstance(store, mfa_code_store.GarminMFACodeStore)

    def test_empty_uri_defaults_to_memory(self):
        store = mfa_code_store.create_garmin_mfa_code_store("")
        assert isinstance(store, mfa_code_store.GarminMFACodeStore)

    def test_unsupported_uri_raises_value_error(self):
        with pytest.raises(ValueError, match="Unsupported Garmin MFA code storage URI scheme"):
            mfa_code_store.create_garmin_mfa_code_store("ftp://example.com")

    def test_redis_uri_returns_redis_store(self):
        with (
            patch("garmin.mfa_code_store.core_redis.is_memory_storage_uri", return_value=False),
            patch("garmin.mfa_code_store.core_redis.is_redis_storage_uri", return_value=True),
            patch("garmin.mfa_code_store.core_redis.create_redis_client", return_value=MagicMock()),
        ):
            store = mfa_code_store.create_garmin_mfa_code_store("redis://localhost:6379/0")
        assert isinstance(store, mfa_code_store.RedisGarminMFACodeStore)


class TestGetGarminMFACodeStore:
    """get_garmin_mfa_code_store: returns the module singleton."""

    def test_returns_garmin_mfa_code_store_instance(self):
        result = mfa_code_store.get_garmin_mfa_code_store()
        assert result is mfa_code_store.garmin_mfa_code_store
