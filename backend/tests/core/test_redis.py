"""Tests for core.redis module."""

from unittest.mock import MagicMock, patch

import pytest
from redis import RedisError

import core.redis as core_redis


class TestRedisStorageUnavailableError:
    """Tests for RedisStorageUnavailableError class."""

    def test_is_runtime_error_subclass(self):
        assert issubclass(core_redis.RedisStorageUnavailableError, RuntimeError)


class TestRaiseRedisStorageUnavailable:
    """Tests for raise_redis_storage_unavailable function."""

    def test_logs_and_raises(self):
        err = RedisError("connection refused")
        with (
            patch("core.redis.core_logger.print_to_log") as mock_log,
            pytest.raises(core_redis.RedisStorageUnavailableError),
        ):
            core_redis.raise_redis_storage_unavailable("cache", "get", err)
        mock_log.assert_called_once()


class TestIsRedisStorageUri:
    """Tests for is_redis_storage_uri function."""

    def test_redis_uri(self):
        assert core_redis.is_redis_storage_uri("redis://localhost:6379") is True

    def test_rediss_uri(self):
        assert core_redis.is_redis_storage_uri("rediss://localhost:6379") is True

    def test_unix_uri(self):
        assert core_redis.is_redis_storage_uri("unix:///tmp/redis.sock") is True

    def test_memory_uri_returns_false(self):
        assert core_redis.is_redis_storage_uri("memory://") is False

    def test_http_uri_returns_false(self):
        assert core_redis.is_redis_storage_uri("http://example.com") is False

    def test_case_insensitive(self):
        assert core_redis.is_redis_storage_uri("REDIS://localhost") is True


class TestIsMemoryStorageUri:
    """Tests for is_memory_storage_uri function."""

    def test_memory_uri(self):
        assert core_redis.is_memory_storage_uri("memory://") is True

    def test_redis_uri_returns_false(self):
        assert core_redis.is_memory_storage_uri("redis://localhost") is False

    def test_case_insensitive(self):
        assert core_redis.is_memory_storage_uri("MEMORY://") is True


class TestDeleteMatchingKeys:
    """Tests for delete_matching_keys function."""

    def test_no_keys(self):
        redis_client = MagicMock()
        redis_client.scan_iter.return_value = iter([])
        result = core_redis.delete_matching_keys(redis_client, "pattern:*")
        assert result == 0
        redis_client.delete.assert_not_called()

    def test_single_batch(self):
        redis_client = MagicMock()
        redis_client.scan_iter.return_value = iter(["key:1", "key:2"])
        redis_client.delete.return_value = 2
        result = core_redis.delete_matching_keys(redis_client, "pattern:*", scan_count=10)
        assert result == 2
        redis_client.delete.assert_called_once_with("key:1", "key:2")

    def test_multiple_batches(self):
        redis_client = MagicMock()
        redis_client.scan_iter.return_value = iter(["k1", "k2", "k3", "k4", "k5"])
        redis_client.delete.side_effect = [3, 2]
        result = core_redis.delete_matching_keys(redis_client, "p:*", scan_count=3)
        assert result == 5
        assert redis_client.delete.call_count == 2
        redis_client.delete.assert_any_call("k1", "k2", "k3")
        redis_client.delete.assert_any_call("k4", "k5")


class TestCreateRedisClient:
    """Tests for create_redis_client function."""

    def test_success(self):
        mock_client = MagicMock()
        with patch("redis.Redis.from_url", return_value=mock_client) as mock_from_url:
            result = core_redis.create_redis_client("redis://localhost", "cache")

        mock_from_url.assert_called_once()
        mock_client.ping.assert_called_once()
        assert result is mock_client

    def test_redis_error_raises_runtime_error(self):
        with (
            patch("redis.Redis.from_url", side_effect=RedisError("fail")),
            pytest.raises(RuntimeError, match="Unable to initialize Redis storage"),
        ):
            core_redis.create_redis_client("redis://localhost", "cache")

    def test_value_error_raises_runtime_error(self):
        with (
            patch("redis.Redis.from_url", side_effect=ValueError("bad uri")),
            pytest.raises(RuntimeError, match="Unable to initialize Redis storage"),
        ):
            core_redis.create_redis_client("bad://uri", "cache")
