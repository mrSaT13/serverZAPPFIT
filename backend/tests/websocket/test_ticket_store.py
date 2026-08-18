"""Tests for websocket.ticket_store module."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from redis import RedisError

from websocket.ticket_store import (
    TICKET_TTL_SECONDS,
    RedisWsTicketStore,
    WsTicketStore,
    WsTicketStoreProtocol,
    WsTicketStoreUnavailableError,
    create_ws_ticket_store,
    get_ws_ticket_store,
)


class TestWsTicketStoreProtocol:
    """Tests for WsTicketStoreProtocol structural checking."""

    def test_in_memory_store_satisfies_protocol(self):
        """WsTicketStore satisfies the WsTicketStoreProtocol."""
        assert isinstance(WsTicketStore(), WsTicketStoreProtocol)

    def test_redis_store_satisfies_protocol(self):
        """RedisWsTicketStore satisfies the WsTicketStoreProtocol."""
        assert isinstance(RedisWsTicketStore(MagicMock()), WsTicketStoreProtocol)


class TestWsTicketStore:
    """Tests for the in-memory WsTicketStore class."""

    @pytest.fixture
    def store(self):
        """Create a fresh WsTicketStore for each test."""
        return WsTicketStore()

    def test_create_ticket_returns_string(self, store):
        """create_ticket returns a non-empty string."""
        ticket = store.create_ticket(user_id=1)
        assert isinstance(ticket, str)
        assert len(ticket) > 0

    def test_create_ticket_unique_per_call(self, store):
        """Each call to create_ticket returns a unique ticket."""
        t1 = store.create_ticket(user_id=1)
        t2 = store.create_ticket(user_id=1)
        assert t1 != t2

    def test_consume_ticket_returns_user_id(self, store):
        """consume_ticket returns the user_id bound to the ticket."""
        ticket = store.create_ticket(user_id=42)
        result = store.consume_ticket(ticket)
        assert result == 42

    def test_consume_ticket_single_use(self, store):
        """A ticket can only be consumed once."""
        ticket = store.create_ticket(user_id=7)
        assert store.consume_ticket(ticket) == 7
        assert store.consume_ticket(ticket) is None

    def test_consume_unknown_ticket_returns_none(self, store):
        """consume_ticket returns None for an unknown ticket string."""
        assert store.consume_ticket("not-a-real-ticket") is None

    def test_consume_expired_ticket_returns_none(self, store):
        """consume_ticket returns None when the ticket has expired."""
        ticket = store.create_ticket(user_id=3)
        with store._lock:
            user_id, _ = store._store[ticket]
            store._store[ticket] = (user_id, datetime.now(UTC) - timedelta(seconds=1))
        assert store.consume_ticket(ticket) is None

    def test_cleanup_removes_expired_entries(self, store):
        """_cleanup_expired_locked removes only expired entries."""
        fresh = store.create_ticket(user_id=1)
        expired = store.create_ticket(user_id=2)
        with store._lock:
            user_id, _ = store._store[expired]
            store._store[expired] = (user_id, datetime.now(UTC) - timedelta(seconds=1))
            store._cleanup_expired_locked()
        assert fresh in store._store
        assert expired not in store._store

    def test_create_ticket_triggers_cleanup(self, store):
        """Creating a ticket removes pre-existing expired entries."""
        expired = store.create_ticket(user_id=5)
        with store._lock:
            uid, _ = store._store[expired]
            store._store[expired] = (uid, datetime.now(UTC) - timedelta(seconds=1))
        store.create_ticket(user_id=6)
        assert expired not in store._store

    def test_ticket_ttl_is_30_seconds(self):
        """TICKET_TTL_SECONDS constant is 30."""
        assert TICKET_TTL_SECONDS == 30

    def test_ticket_expiry_within_ttl(self, store):
        """Newly created ticket expires approximately TICKET_TTL_SECONDS from now."""
        before = datetime.now(UTC)
        store.create_ticket(user_id=1)
        after = datetime.now(UTC)
        for _, (_, exp) in store._store.items():
            assert (
                before + timedelta(seconds=TICKET_TTL_SECONDS) <= exp <= after + timedelta(seconds=TICKET_TTL_SECONDS)
            )


class TestRedisWsTicketStore:
    """Tests for the Redis-backed RedisWsTicketStore class."""

    @pytest.fixture
    def redis_client(self):
        """Create a mock Redis client."""
        return MagicMock()

    @pytest.fixture
    def store(self, redis_client):
        """Create a RedisWsTicketStore backed by a mock Redis client."""
        return RedisWsTicketStore(redis_client)

    def test_create_ticket_returns_string(self, store, redis_client):
        """create_ticket calls Redis SET NX and returns a string ticket."""
        redis_client.set.return_value = True
        ticket = store.create_ticket(user_id=1)
        assert isinstance(ticket, str)
        assert len(ticket) > 0
        redis_client.set.assert_called_once()
        call_kwargs = redis_client.set.call_args
        assert call_kwargs.kwargs["ex"] == TICKET_TTL_SECONDS
        assert call_kwargs.kwargs["nx"] is True

    def test_create_ticket_retries_on_nx_collision(self, store, redis_client):
        """create_ticket retries when SET NX returns falsy (collision)."""
        # First call: NX collision (returns None/False); second call: success
        redis_client.set.side_effect = [None, True]
        ticket = store.create_ticket(user_id=1)
        assert isinstance(ticket, str)
        assert redis_client.set.call_count == 2

    def test_create_ticket_stores_user_id_as_string(self, store, redis_client):
        """create_ticket stores the user ID as a string value."""
        redis_client.set.return_value = True
        store.create_ticket(user_id=42)
        call_args = redis_client.set.call_args
        assert call_args.args[1] == "42"

    def test_consume_ticket_returns_user_id(self, store, redis_client):
        """consume_ticket calls GETDEL and returns int user ID."""
        redis_client.getdel.return_value = "99"
        result = store.consume_ticket("some-ticket")
        assert result == 99
        redis_client.getdel.assert_called_once()

    def test_consume_ticket_returns_none_for_missing(self, store, redis_client):
        """consume_ticket returns None when GETDEL returns None."""
        redis_client.getdel.return_value = None
        assert store.consume_ticket("unknown") is None

    @patch("websocket.ticket_store.core_logger.print_to_log")
    def test_consume_ticket_returns_none_for_corrupt_value(self, mock_log, store, redis_client):
        """consume_ticket returns None and logs a generic warning (no ticket in message)."""
        redis_client.getdel.return_value = "not-an-int"
        result = store.consume_ticket("some-ticket")
        assert result is None
        mock_log.assert_called_once()
        warning_msg = mock_log.call_args.args[0]
        assert "some-ticket" not in warning_msg
        assert "ws:ticket:" not in warning_msg

    def test_create_ticket_raises_on_redis_error(self, store, redis_client):
        """create_ticket raises WsTicketStoreUnavailableError on Redis failure."""
        redis_client.set.side_effect = RedisError("connection refused")
        with pytest.raises(WsTicketStoreUnavailableError):
            store.create_ticket(user_id=1)

    def test_consume_ticket_raises_on_redis_error(self, store, redis_client):
        """consume_ticket raises WsTicketStoreUnavailableError on Redis failure."""
        redis_client.getdel.side_effect = RedisError("connection refused")
        with pytest.raises(WsTicketStoreUnavailableError):
            store.consume_ticket("some-ticket")


class TestCreateWsTicketStore:
    """Tests for the create_ws_ticket_store factory."""

    def test_memory_uri_returns_in_memory_store(self):
        """'memory://' URI produces a WsTicketStore."""
        result = create_ws_ticket_store("memory://")
        assert isinstance(result, WsTicketStore)

    def test_unsupported_uri_raises_value_error(self):
        """An unknown URI scheme raises ValueError."""
        with pytest.raises(ValueError, match="WS_TICKET_STORAGE_URI"):
            create_ws_ticket_store("ftp://unsupported")


class TestGetWsTicketStore:
    """Tests for get_ws_ticket_store dependency."""

    def test_returns_ws_ticket_store_protocol_instance(self):
        """get_ws_ticket_store returns a WsTicketStoreProtocol."""
        result = get_ws_ticket_store()
        assert isinstance(result, WsTicketStoreProtocol)

    def test_returns_singleton(self):
        """get_ws_ticket_store returns the same instance on each call."""
        assert get_ws_ticket_store() is get_ws_ticket_store()
