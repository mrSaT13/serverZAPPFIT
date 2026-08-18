"""
Dedicated tests for auth.security_stores module.

Covers normalize_username_key, username_log_identifier,
RedisFailedLoginAttempts, RedisPendingMFALogin, Redis failure
scenarios, and FastAPI dependency functions.
"""

import hashlib
from datetime import UTC, datetime
from fnmatch import fnmatch

import pytest
from redis import RedisError

import auth.security_stores as security_stores

# ---------------------------------------------------------------------------
# Redis test doubles
# ---------------------------------------------------------------------------


class FakeRedis:
    """
    In-memory Redis test double.

    Attributes:
        values: Stored key-value pairs.
        expirations: Stored key TTLs.
    """

    def __init__(self) -> None:
        """Initialize fake Redis state."""
        self.values: dict = {}
        self.expirations: dict = {}

    def register_script(self, script: str):
        """
        Return a callable that mimics the lockout Lua script.

        Args:
            script: Lua script source (ignored).

        Returns:
            Callable that executes the lockout logic in Python.
        """

        def script_runner(keys, args):
            lockout_key = keys[0]
            attempts_key = keys[1]
            now_epoch = int(args[0])
            attempts_ttl = int(args[1])
            low_threshold = int(args[2])
            low_lockout = int(args[3])
            mid_threshold = int(args[4])
            mid_lockout = int(args[5])
            high_threshold = int(args[6])
            high_lockout = int(args[7])

            lockout_until = self.values.get(lockout_key)
            if lockout_until and int(lockout_until) > now_epoch:
                current_count = int(self.values.get(attempts_key) or 0)
                return [current_count, int(lockout_until), 0]

            if lockout_until:
                self.delete(lockout_key)

            failed_count = int(self.values.get(attempts_key) or 0) + 1
            self.values[attempts_key] = str(failed_count)
            self.expirations[attempts_key] = attempts_ttl

            lockout_seconds = 0
            if failed_count >= high_threshold:
                lockout_seconds = high_lockout
            elif failed_count >= mid_threshold:
                lockout_seconds = mid_lockout
            elif failed_count >= low_threshold:
                lockout_seconds = low_lockout

            if lockout_seconds > 0:
                lockout_until_ts = now_epoch + lockout_seconds
                self.values[lockout_key] = str(lockout_until_ts)
                self.expirations[lockout_key] = lockout_seconds
                return [failed_count, lockout_until_ts, 1]

            return [failed_count, 0, 0]

        return script_runner

    def set(self, key: str, value, ex: int | None = None) -> None:
        """
        Set a fake Redis key.

        Args:
            key: Redis key.
            value: Value to store.
            ex: Optional TTL in seconds.
        """
        self.values[key] = value
        if ex is not None:
            self.expirations[key] = ex

    def get(self, key: str):
        """
        Get a fake Redis key.

        Args:
            key: Redis key.

        Returns:
            Stored value or None.
        """
        return self.values.get(key)

    def getdel(self, key: str):
        """
        Atomically get and delete a fake Redis key.

        Args:
            key: Redis key.

        Returns:
            Stored value or None.
        """
        value = self.values.get(key)
        self.delete(key)
        return value

    def delete(self, *keys: str) -> int:
        """
        Delete one or more fake Redis keys.

        Args:
            keys: Keys to delete.

        Returns:
            Number of keys actually deleted.
        """
        deleted = 0
        for key in keys:
            if key in self.values:
                deleted += 1
            self.values.pop(key, None)
            self.expirations.pop(key, None)
        return deleted

    def scan_iter(self, match=None, count=None):
        """
        Iterate fake Redis keys matching a glob pattern.

        Args:
            match: Optional glob pattern.
            count: Hint for batch size (ignored).

        Returns:
            Generator yielding matching keys.
        """
        for key in list(self.values):
            if match is None or fnmatch(key, match):
                yield key


class FailingRedis(FakeRedis):
    """
    Redis test double that raises RedisError on one operation.

    Attributes:
        failing_operation: Operation name that should raise.
    """

    def __init__(self, failing_operation: str) -> None:
        """
        Initialize failing Redis double.

        Args:
            failing_operation: Operation name to fail on.
        """
        super().__init__()
        self.failing_operation = failing_operation

    def _fail_if_needed(self, operation: str) -> None:
        """
        Raise RedisError when operation matches failing_operation.

        Args:
            operation: Current operation name.

        Raises:
            RedisError: When operation matches failing_operation.
        """
        if self.failing_operation == operation:
            raise RedisError("simulated redis failure")

    def register_script(self, script: str):
        """
        Return a script runner that can fail on execution.

        Args:
            script: Lua script source.

        Returns:
            Callable that raises RedisError on configured op.
        """
        base_runner = super().register_script(script)

        def failing_script_runner(keys, args):
            self._fail_if_needed("script")
            return base_runner(keys, args)

        return failing_script_runner

    def set(self, key: str, value, ex: int | None = None) -> None:
        """
        Set a key or raise RedisError.

        Args:
            key: Redis key.
            value: Value to store.
            ex: Optional TTL in seconds.
        """
        self._fail_if_needed("set")
        super().set(key, value, ex)

    def get(self, key: str):
        """
        Get a key or raise RedisError.

        Args:
            key: Redis key.

        Returns:
            Stored value or None.
        """
        self._fail_if_needed("get")
        return super().get(key)

    def getdel(self, key: str):
        """
        Get and delete a key or raise RedisError.

        Args:
            key: Redis key.

        Returns:
            Stored value or None.
        """
        self._fail_if_needed("getdel")
        return super().getdel(key)

    def delete(self, *keys: str) -> int:
        """
        Delete keys or raise RedisError.

        Args:
            keys: Keys to delete.

        Returns:
            Number of keys deleted.
        """
        self._fail_if_needed("delete")
        return super().delete(*keys)

    def scan_iter(self, match=None, count=None):
        """
        Iterate keys or raise RedisError.

        Args:
            match: Optional glob pattern.
            count: Hint for batch size (ignored).

        Returns:
            Generator yielding matching keys.
        """
        self._fail_if_needed("scan_iter")
        yield from super().scan_iter(match, count)


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------


def _make_failed_login_store(
    redis_client,
) -> security_stores.RedisFailedLoginAttempts:
    """
    Create a RedisFailedLoginAttempts with a custom Redis double.

    Args:
        redis_client: Fake or failing Redis instance.

    Returns:
        RedisFailedLoginAttempts bound to the given client.
    """
    return security_stores.RedisFailedLoginAttempts(redis_client)


def _make_pending_mfa_store(
    redis_client,
) -> security_stores.RedisPendingMFALogin:
    """
    Create a RedisPendingMFALogin with a custom Redis double.

    Args:
        redis_client: Fake or failing Redis instance.

    Returns:
        RedisPendingMFALogin bound to the given client.
    """
    return security_stores.RedisPendingMFALogin(redis_client)


# ---------------------------------------------------------------------------
# Tests: normalize_username_key
# ---------------------------------------------------------------------------


class TestNormalizeUsernameKey:
    """Tests for the normalize_username_key helper function."""

    def test_lowercases_ascii(self):
        """Uppercase ASCII characters are folded to lowercase."""
        result = security_stores.normalize_username_key("TestUser")
        assert result == "testuser"

    def test_strips_leading_trailing_whitespace(self):
        """Leading and trailing whitespace is stripped."""
        result = security_stores.normalize_username_key("  testuser  ")
        assert result == "testuser"

    def test_url_decodes_percent_at(self):
        """Percent-encoded @ sign is decoded to literal @."""
        result = security_stores.normalize_username_key("test%40example.com")
        assert result == "test@example.com"

    def test_url_decodes_percent_20_space(self):
        """Percent-encoded space (%20) is decoded to a literal space."""
        result = security_stores.normalize_username_key("test%20user")
        assert result == "test user"

    def test_plus_sign_converted_to_space(self):
        """A literal + in the username is converted to a space."""
        result = security_stores.normalize_username_key("test+user")
        assert result == "test user"

    def test_percent_2b_url_decoded_then_converted_to_space(self):
        """
        URL-encoded plus (%2B) is first decoded to +,
        then converted to a space.
        """
        result = security_stores.normalize_username_key("test%2Buser")
        assert result == "test user"

    def test_combined_casing_whitespace_and_url_encoding(self):
        """All transformations apply together in correct order."""
        result = security_stores.normalize_username_key("  Test%40Example.COM  ")
        assert result == "test@example.com"

    def test_empty_string_returns_empty_string(self):
        """An empty input normalizes to an empty string."""
        result = security_stores.normalize_username_key("")
        assert result == ""

    def test_already_normalized_is_unchanged(self):
        """A fully normalized username passes through unchanged."""
        result = security_stores.normalize_username_key("testuser")
        assert result == "testuser"

    def test_unicode_casefold(self):
        """casefold is applied so unicode characters normalize."""
        result = security_stores.normalize_username_key("StraBe")
        assert result == "strabe"

    def test_whitespace_only_returns_empty_string(self):
        """A whitespace-only string normalizes to an empty string."""
        result = security_stores.normalize_username_key("   ")
        assert result == ""


# ---------------------------------------------------------------------------
# Tests: username_log_identifier
# ---------------------------------------------------------------------------


class TestUsernameLogIdentifier:
    """Tests for the username_log_identifier helper function."""

    def test_returns_hash_prefix_format(self):
        """Return value starts with 'username_hash='."""
        identifier = security_stores.username_log_identifier("alice")
        assert identifier.startswith("username_hash=")

    def test_does_not_contain_raw_username(self):
        """Raw username must not appear in the log identifier."""
        identifier = security_stores.username_log_identifier("supersensitive@example.com")
        assert "supersensitive" not in identifier
        assert "example.com" not in identifier

    def test_hash_matches_sha256_of_normalized_username(self):
        """Digest equals SHA-256 of the normalized username."""
        raw = " Alice%40Example.COM "
        normalized = "alice@example.com"
        expected = hashlib.sha256(normalized.encode()).hexdigest()
        identifier = security_stores.username_log_identifier(raw)
        assert identifier == f"username_hash={expected}"

    def test_same_canonical_form_same_identifier(self):
        """Different raw forms that normalize identically match."""
        ident_a = security_stores.username_log_identifier("Alice%40Example.COM")
        ident_b = security_stores.username_log_identifier("alice@example.com")
        assert ident_a == ident_b

    def test_different_usernames_different_identifiers(self):
        """Distinct usernames produce distinct log identifiers."""
        ident_a = security_stores.username_log_identifier("alice")
        ident_b = security_stores.username_log_identifier("bob")
        assert ident_a != ident_b


# ---------------------------------------------------------------------------
# Tests: RedisFailedLoginAttempts
# ---------------------------------------------------------------------------


class TestRedisFailedLoginAttempts:
    """Tests for the Redis-backed RedisFailedLoginAttempts store."""

    def test_is_not_locked_out_initially(self):
        """A fresh store reports no lockout for an unknown user."""
        store = _make_failed_login_store(FakeRedis())
        assert store.is_locked_out("alice") is False

    def test_get_lockout_time_returns_none_when_not_locked(self):
        """get_lockout_time returns None when user has no lockout."""
        store = _make_failed_login_store(FakeRedis())
        assert store.get_lockout_time("alice") is None

    def test_first_failed_attempt_returns_one(self):
        """record_failed_attempt returns 1 on the first call."""
        store = _make_failed_login_store(FakeRedis())
        count = store.record_failed_attempt("alice")
        assert count == 1

    def test_subsequent_attempts_increment_count(self):
        """Subsequent calls increment the returned counter."""
        store = _make_failed_login_store(FakeRedis())
        for expected in range(1, 5):
            count = store.record_failed_attempt("alice")
            assert count == expected

    def test_lockout_applied_at_5_attempts(self):
        """is_locked_out returns True after 5 failed attempts."""
        store = _make_failed_login_store(FakeRedis())
        for _ in range(5):
            store.record_failed_attempt("alice")
        assert store.is_locked_out("alice") is True

    def test_lockout_applied_at_10_attempts(self):
        """is_locked_out returns True after 10 failed attempts."""
        store = _make_failed_login_store(FakeRedis())
        for _ in range(10):
            store.record_failed_attempt("alice")
        assert store.is_locked_out("alice") is True

    def test_lockout_applied_at_20_attempts(self):
        """is_locked_out returns True after 20 failed attempts."""
        store = _make_failed_login_store(FakeRedis())
        for _ in range(20):
            store.record_failed_attempt("alice")
        assert store.is_locked_out("alice") is True

    def test_get_lockout_time_returns_future_datetime_when_locked(self):
        """get_lockout_time returns a future datetime after lockout."""
        store = _make_failed_login_store(FakeRedis())
        for _ in range(5):
            store.record_failed_attempt("alice")
        lockout_time = store.get_lockout_time("alice")
        assert lockout_time is not None
        assert lockout_time > datetime.now(UTC)

    def test_count_does_not_increment_while_locked(self):
        """record_failed_attempt returns the same count during lockout."""
        store = _make_failed_login_store(FakeRedis())
        for _ in range(5):
            store.record_failed_attempt("alice")
        count_1 = store.record_failed_attempt("alice")
        count_2 = store.record_failed_attempt("alice")
        assert count_1 == count_2 == 5

    def test_reset_attempts_clears_lockout(self):
        """reset_attempts removes the lockout for a user."""
        store = _make_failed_login_store(FakeRedis())
        for _ in range(5):
            store.record_failed_attempt("alice")
        assert store.is_locked_out("alice") is True
        store.reset_attempts("alice")
        assert store.is_locked_out("alice") is False
        assert store.get_lockout_time("alice") is None

    def test_reset_allows_new_attempts_after_clear(self):
        """After reset_attempts, the counter starts from one again."""
        store = _make_failed_login_store(FakeRedis())
        for _ in range(3):
            store.record_failed_attempt("alice")
        store.reset_attempts("alice")
        count = store.record_failed_attempt("alice")
        assert count == 1

    def test_different_users_tracked_independently(self):
        """Lockout for one username does not affect another."""
        store = _make_failed_login_store(FakeRedis())
        for _ in range(5):
            store.record_failed_attempt("alice")
        assert store.is_locked_out("alice") is True
        assert store.is_locked_out("bob") is False

    def test_username_normalization_collapses_case(self):
        """Attempts recorded under different cases share state."""
        store = _make_failed_login_store(FakeRedis())
        for _ in range(3):
            store.record_failed_attempt("Alice")
        for _ in range(2):
            store.record_failed_attempt("ALICE")
        assert store.is_locked_out("alice") is True

    def test_clear_all_removes_all_records(self):
        """clear_all wipes every stored attempt and lockout."""
        store = _make_failed_login_store(FakeRedis())
        for _ in range(5):
            store.record_failed_attempt("alice")
        store.clear_all()
        assert store.is_locked_out("alice") is False


# ---------------------------------------------------------------------------
# Tests: RedisPendingMFALogin
# ---------------------------------------------------------------------------


class TestRedisPendingMFAStore:
    """Tests for the Redis-backed RedisPendingMFALogin store."""

    def test_add_and_get_pending_login(self):
        """add_pending_login stores user_id retrievable by get."""
        store = _make_pending_mfa_store(FakeRedis())
        store.add_pending_login("alice", 42)
        assert store.get_pending_login("alice") == 42

    def test_get_pending_login_returns_none_for_unknown_user(self):
        """get_pending_login returns None for a missing username."""
        store = _make_pending_mfa_store(FakeRedis())
        assert store.get_pending_login("unknown") is None

    def test_claim_pending_login_returns_user_id(self):
        """claim_pending_login returns the stored user_id."""
        store = _make_pending_mfa_store(FakeRedis())
        store.add_pending_login("alice", 42)
        assert store.claim_pending_login("alice") == 42

    def test_claim_pending_login_removes_entry(self):
        """After claim, the entry is no longer available."""
        store = _make_pending_mfa_store(FakeRedis())
        store.add_pending_login("alice", 42)
        store.claim_pending_login("alice")
        assert store.get_pending_login("alice") is None

    def test_claim_pending_login_returns_none_when_not_found(self):
        """claim_pending_login returns None for a missing entry."""
        store = _make_pending_mfa_store(FakeRedis())
        assert store.claim_pending_login("unknown") is None

    def test_claim_is_atomic_get_and_delete(self):
        """Consecutive claims return user_id then None."""
        store = _make_pending_mfa_store(FakeRedis())
        store.add_pending_login("alice", 42)
        first = store.claim_pending_login("alice")
        second = store.claim_pending_login("alice")
        assert first == 42
        assert second is None

    def test_delete_pending_login_removes_entry(self):
        """delete_pending_login removes the stored entry."""
        store = _make_pending_mfa_store(FakeRedis())
        store.add_pending_login("alice", 42)
        store.delete_pending_login("alice")
        assert store.get_pending_login("alice") is None

    def test_delete_pending_login_on_missing_user_is_safe(self):
        """delete_pending_login does not raise for unknown username."""
        store = _make_pending_mfa_store(FakeRedis())
        store.delete_pending_login("nobody")  # must not raise

    def test_has_pending_login_true_when_exists(self):
        """has_pending_login returns True when entry exists."""
        store = _make_pending_mfa_store(FakeRedis())
        store.add_pending_login("alice", 42)
        assert store.has_pending_login("alice") is True

    def test_has_pending_login_false_when_missing(self):
        """has_pending_login returns False when entry is absent."""
        store = _make_pending_mfa_store(FakeRedis())
        assert store.has_pending_login("unknown") is False

    def test_clear_for_user_removes_matching_entry(self):
        """clear_for_user removes pending entry belonging to user."""
        store = _make_pending_mfa_store(FakeRedis())
        store.add_pending_login("alice", 42)
        removed = store.clear_for_user(42)
        assert removed == 1
        assert store.get_pending_login("alice") is None

    def test_clear_for_user_returns_zero_when_no_match(self):
        """clear_for_user returns 0 when no entry matches user_id."""
        store = _make_pending_mfa_store(FakeRedis())
        store.add_pending_login("alice", 99)
        removed = store.clear_for_user(42)
        assert removed == 0
        assert store.get_pending_login("alice") == 99

    def test_clear_for_user_removes_only_matching_entries(self):
        """clear_for_user leaves entries with different user IDs."""
        store = _make_pending_mfa_store(FakeRedis())
        store.add_pending_login("alice", 42)
        store.add_pending_login("bob", 99)
        removed = store.clear_for_user(42)
        assert removed == 1
        assert store.get_pending_login("alice") is None
        assert store.get_pending_login("bob") == 99

    def test_username_normalization_in_add_and_get(self):
        """add with mixed case is retrievable with normalized form."""
        store = _make_pending_mfa_store(FakeRedis())
        store.add_pending_login("Alice", 42)
        assert store.get_pending_login("alice") == 42

    def test_is_not_locked_out_initially(self):
        """A fresh store reports no MFA lockout for an unknown user."""
        store = _make_pending_mfa_store(FakeRedis())
        assert store.is_locked_out("alice") is False

    def test_lockout_applied_at_5_mfa_failures(self):
        """is_locked_out returns True after 5 failed MFA attempts."""
        store = _make_pending_mfa_store(FakeRedis())
        for _ in range(5):
            store.record_failed_attempt("alice")
        assert store.is_locked_out("alice") is True

    def test_lockout_applied_at_10_mfa_failures(self):
        """is_locked_out returns True after 10 failed MFA attempts."""
        store = _make_pending_mfa_store(FakeRedis())
        for _ in range(10):
            store.record_failed_attempt("alice")
        assert store.is_locked_out("alice") is True

    def test_lockout_applied_at_15_mfa_failures(self):
        """is_locked_out returns True after 15 failed MFA attempts."""
        store = _make_pending_mfa_store(FakeRedis())
        for _ in range(15):
            store.record_failed_attempt("alice")
        assert store.is_locked_out("alice") is True

    def test_get_lockout_time_returns_future_when_locked(self):
        """get_lockout_time returns a future datetime when locked."""
        store = _make_pending_mfa_store(FakeRedis())
        for _ in range(5):
            store.record_failed_attempt("alice")
        lockout_time = store.get_lockout_time("alice")
        assert lockout_time is not None
        assert lockout_time > datetime.now(UTC)

    def test_reset_failed_attempts_clears_mfa_lockout(self):
        """reset_attempts removes the MFA lockout."""
        store = _make_pending_mfa_store(FakeRedis())
        for _ in range(5):
            store.record_failed_attempt("alice")
        store.reset_attempts("alice")
        assert store.is_locked_out("alice") is False
        assert store.get_lockout_time("alice") is None

    def test_mfa_and_login_stores_use_separate_key_namespaces(self):
        """
        A lockout in the MFA store is independent of the login store.
        """
        fake = FakeRedis()
        login_store = _make_failed_login_store(fake)
        mfa_store = _make_pending_mfa_store(fake)
        for _ in range(5):
            mfa_store.record_failed_attempt("alice")
        assert mfa_store.is_locked_out("alice") is True
        assert login_store.is_locked_out("alice") is False

    def test_cleanup_expired_returns_zero(self):
        """cleanup_expired returns 0 (Redis handles TTL natively)."""
        store = _make_pending_mfa_store(FakeRedis())
        store.add_pending_login("alice", 42)
        assert store.cleanup_expired() == 0


# ---------------------------------------------------------------------------
# Tests: Redis failure scenarios
# ---------------------------------------------------------------------------


class TestRedisFailureScenarios:
    """
    Tests that Redis failures surface as AuthSecurityStoreUnavailableError.

    Each test uses FailingRedis to inject a RedisError at the
    specific operation that each method relies on.
    """

    # -- RedisFailedLoginAttempts --

    def test_record_failed_attempt_raises_on_script_error(self):
        """
        record_failed_attempt raises AuthSecurityStoreUnavailableError
        when the Lua script call fails.
        """
        store = _make_failed_login_store(FailingRedis("script"))
        with pytest.raises(security_stores.AuthSecurityStoreUnavailableError):
            store.record_failed_attempt("alice")

    def test_is_locked_out_raises_on_get_error(self):
        """
        is_locked_out raises AuthSecurityStoreUnavailableError when
        the Redis GET fails.
        """
        store = _make_failed_login_store(FailingRedis("get"))
        with pytest.raises(security_stores.AuthSecurityStoreUnavailableError):
            store.is_locked_out("alice")

    def test_get_lockout_time_raises_on_get_error(self):
        """
        get_lockout_time raises AuthSecurityStoreUnavailableError when
        the Redis GET fails.
        """
        store = _make_failed_login_store(FailingRedis("get"))
        with pytest.raises(security_stores.AuthSecurityStoreUnavailableError):
            store.get_lockout_time("alice")

    def test_reset_attempts_raises_on_delete_error(self):
        """
        reset_attempts raises AuthSecurityStoreUnavailableError when
        the Redis DELETE fails.
        """
        store = _make_failed_login_store(FailingRedis("delete"))
        with pytest.raises(security_stores.AuthSecurityStoreUnavailableError):
            store.reset_attempts("alice")

    def test_failed_login_clear_all_raises_on_scan_error(self):
        """
        clear_all raises AuthSecurityStoreUnavailableError when the
        Redis SCAN fails.
        """
        store = _make_failed_login_store(FailingRedis("scan_iter"))
        with pytest.raises(security_stores.AuthSecurityStoreUnavailableError):
            store.clear_all()

    # -- RedisPendingMFALogin --

    def test_add_pending_login_raises_on_set_error(self):
        """
        add_pending_login raises AuthSecurityStoreUnavailableError when
        the Redis SET fails.
        """
        store = _make_pending_mfa_store(FailingRedis("set"))
        with pytest.raises(security_stores.AuthSecurityStoreUnavailableError):
            store.add_pending_login("alice", 42)

    def test_get_pending_login_raises_on_get_error(self):
        """
        get_pending_login raises AuthSecurityStoreUnavailableError when
        the Redis GET fails.
        """
        store = _make_pending_mfa_store(FailingRedis("get"))
        with pytest.raises(security_stores.AuthSecurityStoreUnavailableError):
            store.get_pending_login("alice")

    def test_claim_pending_login_raises_on_getdel_error(self):
        """
        claim_pending_login raises AuthSecurityStoreUnavailableError
        when the Redis GETDEL fails.
        """
        store = _make_pending_mfa_store(FailingRedis("getdel"))
        with pytest.raises(security_stores.AuthSecurityStoreUnavailableError):
            store.claim_pending_login("alice")

    def test_delete_pending_login_raises_on_delete_error(self):
        """
        delete_pending_login raises AuthSecurityStoreUnavailableError
        when the Redis DELETE fails.
        """
        store = _make_pending_mfa_store(FailingRedis("delete"))
        with pytest.raises(security_stores.AuthSecurityStoreUnavailableError):
            store.delete_pending_login("alice")

    def test_pending_mfa_record_failed_raises_on_script_error(self):
        """
        record_failed_attempt raises AuthSecurityStoreUnavailableError
        when the Lua script call fails (MFA store).
        """
        store = _make_pending_mfa_store(FailingRedis("script"))
        with pytest.raises(security_stores.AuthSecurityStoreUnavailableError):
            store.record_failed_attempt("alice")

    def test_pending_mfa_is_locked_out_raises_on_get_error(self):
        """
        is_locked_out raises AuthSecurityStoreUnavailableError when
        the Redis GET fails (MFA store).
        """
        store = _make_pending_mfa_store(FailingRedis("get"))
        with pytest.raises(security_stores.AuthSecurityStoreUnavailableError):
            store.is_locked_out("alice")

    def test_pending_mfa_get_lockout_time_raises_on_get_error(self):
        """
        get_lockout_time raises AuthSecurityStoreUnavailableError when
        the Redis GET fails (MFA store).
        """
        store = _make_pending_mfa_store(FailingRedis("get"))
        with pytest.raises(security_stores.AuthSecurityStoreUnavailableError):
            store.get_lockout_time("alice")

    def test_pending_mfa_reset_raises_on_delete_error(self):
        """
        reset_attempts raises AuthSecurityStoreUnavailableError
        when the Redis DELETE fails (MFA store).
        """
        store = _make_pending_mfa_store(FailingRedis("delete"))
        with pytest.raises(security_stores.AuthSecurityStoreUnavailableError):
            store.reset_attempts("alice")

    def test_clear_for_user_raises_on_scan_error(self):
        """
        clear_for_user raises AuthSecurityStoreUnavailableError when
        the Redis SCAN fails.
        """
        store = _make_pending_mfa_store(FailingRedis("scan_iter"))
        with pytest.raises(security_stores.AuthSecurityStoreUnavailableError):
            store.clear_for_user(42)

    def test_pending_mfa_clear_all_raises_on_scan_error(self):
        """
        clear_all raises AuthSecurityStoreUnavailableError when the
        Redis SCAN fails (MFA store).
        """
        store = _make_pending_mfa_store(FailingRedis("scan_iter"))
        with pytest.raises(security_stores.AuthSecurityStoreUnavailableError):
            store.clear_all()


# ---------------------------------------------------------------------------
# Tests: FastAPI dependency functions
# ---------------------------------------------------------------------------


class TestDependencyFunctions:
    """Tests for get_failed_login_attempts and get_pending_mfa_store."""

    def test_get_failed_login_attempts_returns_store_instance(self):
        """
        get_failed_login_attempts returns a FailedLoginStore
        instance (FailedLoginAttempts or RedisFailedLoginAttempts).
        """
        store = security_stores.get_failed_login_attempts()
        assert isinstance(
            store,
            (
                security_stores.FailedLoginAttempts,
                security_stores.RedisFailedLoginAttempts,
            ),
        )

    def test_get_pending_mfa_store_returns_store_instance(self):
        """
        get_pending_mfa_store returns a PendingMFAStore instance
        (PendingMFALogin or RedisPendingMFALogin).
        """
        store = security_stores.get_pending_mfa_store()
        assert isinstance(
            store,
            (
                security_stores.PendingMFALogin,
                security_stores.RedisPendingMFALogin,
            ),
        )

    def test_get_failed_login_attempts_returns_singleton(self):
        """Repeated calls return the same object instance."""
        store_a = security_stores.get_failed_login_attempts()
        store_b = security_stores.get_failed_login_attempts()
        assert store_a is store_b

    def test_get_pending_mfa_store_returns_singleton(self):
        """Repeated calls return the same object instance."""
        store_a = security_stores.get_pending_mfa_store()
        store_b = security_stores.get_pending_mfa_store()
        assert store_a is store_b


# ---------------------------------------------------------------------------
# Tests: AuthSecurityStoreUnavailableError exception
# ---------------------------------------------------------------------------


class TestAuthSecurityStoreUnavailableError:
    """Tests for the AuthSecurityStoreUnavailableError exception class."""

    def test_is_runtime_error_subclass(self):
        """AuthSecurityStoreUnavailableError is a subclass of RuntimeError."""
        exc = security_stores.AuthSecurityStoreUnavailableError("test")
        assert isinstance(exc, RuntimeError)

    def test_can_be_raised_and_caught(self):
        """The exception can be raised and caught by type."""
        with pytest.raises(
            security_stores.AuthSecurityStoreUnavailableError,
            match="unavailable",
        ):
            raise security_stores.AuthSecurityStoreUnavailableError("unavailable")

    def test_has_descriptive_message(self):
        """The exception preserves the message argument."""
        exc = security_stores.AuthSecurityStoreUnavailableError("oops")
        assert "oops" in str(exc)
