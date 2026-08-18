"""
Tests for auth.schema module.

This module tests Pydantic schemas and dependency classes for authentication,
including login requests, MFA management, and failed attempt tracking.
"""

import hashlib
from datetime import UTC, datetime, timedelta
from fnmatch import fnmatch
from threading import Event, Thread
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from redis import RedisError

import auth.router as auth_router
import auth.schema as auth_schema
import auth.security_stores as auth_security_stores
import core.redis as core_redis


class FakeRedis:
    """Small Redis test double for auth security stores."""

    def __init__(self):
        """Initialize fake Redis state."""
        self.values = {}
        self.expirations = {}

    def register_script(self, script):
        """Return a callable that mimics the lockout Lua script."""

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
                lockout_until = now_epoch + lockout_seconds
                self.values[lockout_key] = str(lockout_until)
                self.expirations[lockout_key] = lockout_seconds
                return [failed_count, lockout_until, 1]

            return [failed_count, 0, 0]

        return script_runner

    def set(self, key, value, ex=None):
        """Set a fake Redis key."""
        self.values[key] = value
        if ex is not None:
            self.expirations[key] = ex

    def get(self, key):
        """Get a fake Redis key."""
        return self.values.get(key)

    def getdel(self, key):
        """Atomically get and delete a fake Redis key."""
        value = self.values.get(key)
        self.delete(key)
        return value

    def delete(self, *keys):
        """Delete fake Redis keys."""
        deleted_count = 0
        for key in keys:
            if key in self.values:
                deleted_count += 1
            self.values.pop(key, None)
            self.expirations.pop(key, None)
        return deleted_count

    def scan_iter(self, match=None, count=None):
        """Iterate fake Redis keys matching a glob pattern."""
        for key in list(self.values):
            if match is None or fnmatch(key, match):
                yield key


class FailingRedis(FakeRedis):
    """Redis test double that raises for one operation."""

    def __init__(self, failing_operation):
        """Initialize the failing fake Redis client."""
        super().__init__()
        self.failing_operation = failing_operation

    def _fail_if_needed(self, operation):
        """Raise RedisError for the configured operation."""
        if self.failing_operation == operation:
            raise RedisError("redis unavailable")

    def register_script(self, script):
        """Return a script runner that can fail on execution."""
        script_runner = super().register_script(script)

        def failing_script_runner(keys, args):
            self._fail_if_needed("script")
            return script_runner(keys, args)

        return failing_script_runner

    def set(self, key, value, ex=None):
        """Set a key or raise RedisError."""
        self._fail_if_needed("set")
        return super().set(key, value, ex)

    def get(self, key):
        """Get a key or raise RedisError."""
        self._fail_if_needed("get")
        return super().get(key)

    def getdel(self, key):
        """Get and delete a key or raise RedisError."""
        self._fail_if_needed("getdel")
        return super().getdel(key)

    def delete(self, *keys):
        """Delete keys or raise RedisError."""
        self._fail_if_needed("delete")
        return super().delete(*keys)

    def scan_iter(self, match=None, count=None):
        """Iterate keys or raise RedisError."""
        self._fail_if_needed("scan_iter")
        yield from super().scan_iter(match, count)


class TestLoginRequest:
    """Tests for LoginRequest Pydantic model."""

    def test_login_request_valid(self):
        """Test valid login request."""
        request = auth_schema.LoginRequest(username="testuser", password="Password1!")
        assert request.username == "testuser"
        assert request.password == "Password1!"

    def test_login_request_username_too_short(self):
        """Test login request with empty username."""
        with pytest.raises(ValidationError) as exc_info:
            auth_schema.LoginRequest(username="", password="Password1!")
        assert "username" in str(exc_info.value)

    def test_login_request_username_too_long(self):
        """Test login request with username exceeding max length."""
        with pytest.raises(ValidationError) as exc_info:
            auth_schema.LoginRequest(username="a" * 251, password="Password1!")
        assert "username" in str(exc_info.value)

    def test_login_request_password_too_short(self):
        """Test login request with password less than 8 characters."""
        with pytest.raises(ValidationError) as exc_info:
            auth_schema.LoginRequest(username="testuser", password="Pass1!")
        assert "password" in str(exc_info.value)


class TestMFALoginRequest:
    """Tests for MFALoginRequest Pydantic model."""

    def test_mfa_login_request_valid(self):
        """Test valid MFA login request with 6-digit code."""
        request = auth_schema.MFALoginRequest(username="testuser", mfa_code="123456")
        assert request.username == "testuser"
        assert request.mfa_code == "123456"

    def test_mfa_login_request_invalid_code_format_letters(self):
        """Test MFA login request with non-numeric code."""
        with pytest.raises(ValidationError) as exc_info:
            auth_schema.MFALoginRequest(username="testuser", mfa_code="12345a")
        assert "mfa_code" in str(exc_info.value)

    def test_mfa_login_request_invalid_code_too_short(self):
        """Test MFA login request with code less than 6 digits."""
        with pytest.raises(ValidationError) as exc_info:
            auth_schema.MFALoginRequest(username="testuser", mfa_code="12345")
        assert "mfa_code" in str(exc_info.value)

    def test_mfa_login_request_invalid_code_too_long(self):
        """Test MFA login request with code more than 6 digits."""
        with pytest.raises(ValidationError) as exc_info:
            auth_schema.MFALoginRequest(username="testuser", mfa_code="1234567")
        assert "mfa_code" in str(exc_info.value)


class TestMFARequiredResponse:
    """Tests for MFARequiredResponse Pydantic model."""

    def test_mfa_required_response_defaults(self):
        """Test MFA required response with default values."""
        response = auth_schema.MFARequiredResponse(username="testuser")
        assert response.mfa_required is True
        assert response.username == "testuser"
        assert response.message == "MFA verification required"

    def test_mfa_required_response_custom_message(self):
        """Test MFA required response with custom message."""
        response = auth_schema.MFARequiredResponse(username="testuser", message="Custom MFA message")
        assert response.mfa_required is True
        assert response.message == "Custom MFA message"

    def test_mfa_required_response_explicit_false(self):
        """Test MFA required response with explicit False."""
        response = auth_schema.MFARequiredResponse(mfa_required=False, username="testuser")
        assert response.mfa_required is False


class TestUsernameLogIdentifier:
    """Tests for auth username log identifiers."""

    def test_username_log_identifier_hashes_normalized_username(self):
        """Test log identifier does not contain raw username."""
        raw_username = " Test.User%2BOne@example.com "
        normalized_username = "test.user one@example.com"
        expected_digest = hashlib.sha256(normalized_username.encode()).hexdigest()

        log_identifier = auth_security_stores.username_log_identifier(raw_username)

        assert log_identifier == f"username_hash={expected_digest}"
        assert "Test.User" not in log_identifier
        assert "example.com" not in log_identifier


class TestPendingMFALogin:
    """Tests for PendingMFALogin class."""

    def test_add_and_get_pending_login(self):
        """Test adding and retrieving pending MFA login."""
        store = auth_security_stores.PendingMFALogin()
        store.add_pending_login("testuser", 123)
        assert store.get_pending_login("testuser") == 123

    def test_claim_pending_login_consumes_entry(self):
        """Test claiming pending MFA login consumes it once."""
        store = auth_security_stores.PendingMFALogin()
        store.add_pending_login("testuser", 123)

        assert store.claim_pending_login("testuser") == 123
        assert store.claim_pending_login("testuser") is None
        assert store.get_pending_login("testuser") is None

    def test_get_pending_login_not_found(self):
        """Test getting non-existent pending login returns None."""
        store = auth_security_stores.PendingMFALogin()
        assert store.get_pending_login("nonexistent") is None

    def test_has_pending_login(self):
        """Test checking if username has pending login."""
        store = auth_security_stores.PendingMFALogin()
        store.add_pending_login("testuser", 123)
        assert store.has_pending_login("testuser") is True
        assert store.has_pending_login("nonexistent") is False

    def test_delete_pending_login(self):
        """Test deleting pending login."""
        store = auth_security_stores.PendingMFALogin()
        store.add_pending_login("testuser", 123)
        store.delete_pending_login("testuser")
        assert store.get_pending_login("testuser") is None

    def test_delete_nonexistent_pending_login(self):
        """Test deleting non-existent pending login doesn't raise error."""
        store = auth_security_stores.PendingMFALogin()
        store.delete_pending_login("nonexistent")  # Should not raise

    def test_clear_all(self):
        """Test clearing all pending logins."""
        store = auth_security_stores.PendingMFALogin()
        store.add_pending_login("user1", 1)
        store.add_pending_login("user2", 2)
        store.clear_all()
        assert store.get_pending_login("user1") is None
        assert store.get_pending_login("user2") is None

    def test_is_not_locked_out_initially(self):
        """Test user is not locked out initially."""
        store = auth_security_stores.PendingMFALogin()
        assert store.is_locked_out("testuser") is False

    def test_lockout_after_5_failures(self):
        """Test 5-minute lockout after 5 failed attempts."""
        store = auth_security_stores.PendingMFALogin()
        for _ in range(5):
            store.record_failed_attempt("testuser")
        assert store.is_locked_out("testuser") is True
        lockout_time = store.get_lockout_time("testuser")
        assert lockout_time is not None
        assert lockout_time > datetime.now(UTC)

    def test_record_failed_attempt_uses_lock(self):
        """Test in-memory MFA attempt updates use the store lock."""
        store = auth_security_stores.PendingMFALogin()
        started = Event()
        finished = Event()
        results = []

        def record_attempt():
            """Record an attempt in a background thread."""
            started.set()
            results.append(store.record_failed_attempt("testuser"))
            finished.set()

        store._lockout._lock.acquire()
        try:
            thread = Thread(target=record_attempt)
            thread.start()
            assert started.wait(timeout=1)
            assert not finished.wait(timeout=0.05)
        finally:
            store._lockout._lock.release()

        thread.join(timeout=1)
        assert results == [1]

    def test_lockout_after_10_failures(self):
        """Test 30-minute lockout after 10 failed attempts."""
        store = auth_security_stores.PendingMFALogin()
        for _ in range(10):
            store.record_failed_attempt("testuser")
        assert store.is_locked_out("testuser") is True

    def test_lockout_after_15_failures(self):
        """Test 2-hour lockout after 15 failed attempts."""
        store = auth_security_stores.PendingMFALogin()
        for _ in range(15):
            store.record_failed_attempt("testuser")
        assert store.is_locked_out("testuser") is True

    def test_failed_attempt_count_doesnt_increment_while_locked(self):
        """Test failed attempt counter doesn't increment during lockout."""
        store = auth_security_stores.PendingMFALogin()
        for _ in range(5):
            store.record_failed_attempt("testuser")
        # Try to increment during lockout
        count_before = store.record_failed_attempt("testuser")
        count_after = store.record_failed_attempt("testuser")
        assert count_before == count_after

    def test_reset_failed_attempts(self):
        """Test resetting failed attempts on successful verification."""
        store = auth_security_stores.PendingMFALogin()
        store.record_failed_attempt("testuser")
        store.record_failed_attempt("testuser")
        store.reset_attempts("testuser")
        assert store.is_locked_out("testuser") is False
        assert store.get_lockout_time("testuser") is None

    def test_get_lockout_time_returns_none_when_not_locked(self):
        """Test get_lockout_time returns None when user not locked."""
        store = auth_security_stores.PendingMFALogin()
        assert store.get_lockout_time("testuser") is None

    def test_clear_all_clears_failed_attempts(self):
        """Test clear_all() clears both pending logins and failed attempts."""
        store = auth_security_stores.PendingMFALogin()
        store.add_pending_login("testuser", 123)
        for _ in range(5):
            store.record_failed_attempt("testuser")
        store.clear_all()
        assert store.is_locked_out("testuser") is False


class TestFailedLoginAttempts:
    """Tests for FailedLoginAttempts class."""

    def test_is_not_locked_out_initially(self):
        """Test user is not locked out initially."""
        tracker = auth_security_stores.FailedLoginAttempts()
        assert tracker.is_locked_out("testuser") is False

    def test_lockout_after_5_failures(self):
        """Test 5-minute lockout after 5 failed login attempts."""
        tracker = auth_security_stores.FailedLoginAttempts()
        for _ in range(5):
            tracker.record_failed_attempt("testuser")
        assert tracker.is_locked_out("testuser") is True
        lockout_time = tracker.get_lockout_time("testuser")
        assert lockout_time is not None
        assert lockout_time > datetime.now(UTC)

    def test_lockout_after_10_failures(self):
        """Test 30-minute lockout after 10 failed login attempts."""
        tracker = auth_security_stores.FailedLoginAttempts()
        for _ in range(10):
            tracker.record_failed_attempt("testuser")
        assert tracker.is_locked_out("testuser") is True

    def test_lockout_after_20_failures(self):
        """Test 24-hour lockout after 20 failed login attempts."""
        tracker = auth_security_stores.FailedLoginAttempts()
        for _ in range(20):
            tracker.record_failed_attempt("testuser")
        assert tracker.is_locked_out("testuser") is True

    def test_failed_attempt_count_returns_correctly(self):
        """Test record_failed_attempt returns current count."""
        tracker = auth_security_stores.FailedLoginAttempts()
        count1 = tracker.record_failed_attempt("testuser")
        count2 = tracker.record_failed_attempt("testuser")
        count3 = tracker.record_failed_attempt("testuser")
        assert count1 == 1
        assert count2 == 2
        assert count3 == 3

    def test_record_failed_attempt_uses_lock(self):
        """Test in-memory login attempt updates use the store lock."""
        tracker = auth_security_stores.FailedLoginAttempts()
        started = Event()
        finished = Event()
        results = []

        def record_attempt():
            """Record an attempt in a background thread."""
            started.set()
            results.append(tracker.record_failed_attempt("testuser"))
            finished.set()

        tracker._lockout._lock.acquire()
        try:
            thread = Thread(target=record_attempt)
            thread.start()
            assert started.wait(timeout=1)
            assert not finished.wait(timeout=0.05)
        finally:
            tracker._lockout._lock.release()

        thread.join(timeout=1)
        assert results == [1]

    def test_failed_attempt_count_doesnt_increment_while_locked(self):
        """Test failed attempt counter doesn't increment during lockout."""
        tracker = auth_security_stores.FailedLoginAttempts()
        for _ in range(5):
            tracker.record_failed_attempt("testuser")
        # Try to increment during lockout
        count_before = tracker.record_failed_attempt("testuser")
        count_after = tracker.record_failed_attempt("testuser")
        assert count_before == count_after

    def test_reset_attempts(self):
        """Test resetting failed attempts on successful login."""
        tracker = auth_security_stores.FailedLoginAttempts()
        tracker.record_failed_attempt("testuser")
        tracker.record_failed_attempt("testuser")
        tracker.reset_attempts("testuser")
        assert tracker.is_locked_out("testuser") is False
        assert tracker.get_lockout_time("testuser") is None

    def test_get_lockout_time_returns_none_when_not_locked(self):
        """Test get_lockout_time returns None when user not locked."""
        tracker = auth_security_stores.FailedLoginAttempts()
        assert tracker.get_lockout_time("testuser") is None

    def test_clear_all(self):
        """Test clearing all failed attempt records."""
        tracker = auth_security_stores.FailedLoginAttempts()
        tracker.record_failed_attempt("user1")
        tracker.record_failed_attempt("user2")
        tracker.clear_all()
        assert tracker.is_locked_out("user1") is False
        assert tracker.is_locked_out("user2") is False

    def test_different_users_tracked_independently(self):
        """Test different users have independent failed attempt tracking."""
        tracker = auth_security_stores.FailedLoginAttempts()
        for _ in range(3):
            tracker.record_failed_attempt("user1")
        for _ in range(5):
            tracker.record_failed_attempt("user2")
        assert tracker.is_locked_out("user1") is False
        assert tracker.is_locked_out("user2") is True


class TestRedisAuthSecurityStores:
    """Tests for Redis-backed auth security stores."""

    def test_auth_store_unavailable_maps_to_http_503(self):
        """Test auth store outage returns a controlled API error."""
        with pytest.raises(HTTPException) as exc_info:
            auth_router._raise_auth_security_store_unavailable(auth_security_stores.AuthSecurityStoreUnavailableError())

        assert exc_info.value.status_code == 503
        assert exc_info.value.detail == ("Authentication temporarily unavailable")

    def test_redis_failed_login_attempts_lockout(self):
        """Test Redis login attempts lock after 5 failures."""
        tracker = auth_security_stores.RedisFailedLoginAttempts(FakeRedis())

        for _ in range(5):
            failed_count = tracker.record_failed_attempt("TestUser")

        assert failed_count == 5
        assert tracker.is_locked_out("testuser") is True
        assert tracker.record_failed_attempt("testuser") == 5

    def test_redis_failed_login_attempts_reset(self):
        """Test Redis login attempt reset deletes lockout state."""
        tracker = auth_security_stores.RedisFailedLoginAttempts(FakeRedis())

        for _ in range(5):
            tracker.record_failed_attempt("testuser")

        tracker.reset_attempts("testuser")

        assert tracker.is_locked_out("testuser") is False
        assert tracker.get_lockout_time("testuser") is None

    def test_redis_failed_login_attempts_get_failure_is_sanitized(self):
        """Test Redis get errors become auth-store outage errors."""
        tracker = auth_security_stores.RedisFailedLoginAttempts(FailingRedis("get"))

        with pytest.raises(auth_security_stores.AuthSecurityStoreUnavailableError) as exc_info:
            tracker.is_locked_out("testuser")

        assert isinstance(
            exc_info.value.__cause__,
            core_redis.RedisStorageUnavailableError,
        )

    def test_redis_failed_login_attempts_script_failure_is_sanitized(self):
        """Test Redis script errors become auth-store outage errors."""
        tracker = auth_security_stores.RedisFailedLoginAttempts(FailingRedis("script"))

        with pytest.raises(auth_security_stores.AuthSecurityStoreUnavailableError):
            tracker.record_failed_attempt("testuser")

    def test_redis_pending_mfa_login_lifecycle(self):
        """Test Redis pending MFA add, get, and delete."""
        store = auth_security_stores.RedisPendingMFALogin(FakeRedis())

        store.add_pending_login("TestUser", 123)

        assert store.get_pending_login("testuser") == 123
        assert store.has_pending_login("testuser") is True

        store.delete_pending_login("testuser")

        assert store.get_pending_login("testuser") is None

    def test_redis_pending_mfa_claim_consumes_entry(self):
        """Test Redis pending MFA claim atomically consumes entry."""
        store = auth_security_stores.RedisPendingMFALogin(FakeRedis())
        store.add_pending_login("TestUser", 123)

        assert store.claim_pending_login("testuser") == 123
        assert store.claim_pending_login("testuser") is None
        assert store.get_pending_login("testuser") is None

    def test_redis_pending_mfa_set_failure_is_sanitized(self):
        """Test Redis pending MFA set errors are sanitized."""
        store = auth_security_stores.RedisPendingMFALogin(FailingRedis("set"))

        with pytest.raises(auth_security_stores.AuthSecurityStoreUnavailableError):
            store.add_pending_login("testuser", 123)

    def test_redis_pending_mfa_claim_failure_is_sanitized(self):
        """Test Redis pending MFA claim errors are sanitized."""
        store = auth_security_stores.RedisPendingMFALogin(FailingRedis("getdel"))

        with pytest.raises(auth_security_stores.AuthSecurityStoreUnavailableError) as exc_info:
            store.claim_pending_login("testuser")

        assert isinstance(
            exc_info.value.__cause__,
            core_redis.RedisStorageUnavailableError,
        )

    def test_redis_pending_mfa_invalid_user_id_is_evicted(self):
        """Test invalid Redis pending MFA payload is removed."""
        redis_client = FakeRedis()
        store = auth_security_stores.RedisPendingMFALogin(redis_client)
        pending_key = store._pending_key("testuser")
        redis_client.set(pending_key, "invalid")

        assert store.get_pending_login("testuser") is None
        assert redis_client.get(pending_key) is None

    def test_redis_pending_mfa_clear_all(self):
        """Test Redis pending MFA clear removes pending and lockout keys."""
        redis_client = FakeRedis()
        store = auth_security_stores.RedisPendingMFALogin(redis_client)
        store.add_pending_login("testuser", 123)

        for _ in range(5):
            store.record_failed_attempt("testuser")

        store.clear_all()

        assert store.get_pending_login("testuser") is None
        assert store.is_locked_out("testuser") is False

    def test_create_auth_security_stores_memory_uri(self):
        """Test memory URI creates memory-backed stores."""
        failed_store, pending_store = auth_security_stores.create_auth_security_stores("memory://")

        assert isinstance(
            failed_store,
            auth_security_stores.FailedLoginAttempts,
        )
        assert isinstance(pending_store, auth_security_stores.PendingMFALogin)

    def test_create_auth_security_stores_blank_uri(self):
        """Test blank URI falls back to memory-backed stores."""
        failed_store, pending_store = auth_security_stores.create_auth_security_stores("")

        assert isinstance(
            failed_store,
            auth_security_stores.FailedLoginAttempts,
        )
        assert isinstance(pending_store, auth_security_stores.PendingMFALogin)

    def test_create_auth_security_stores_redis_uri(self, monkeypatch):
        """Test Redis URI creates Redis-backed stores."""
        monkeypatch.setattr(
            auth_security_stores.core_redis,
            "create_redis_client",
            lambda storage_uri, purpose: FakeRedis(),
        )

        failed_store, pending_store = auth_security_stores.create_auth_security_stores("redis://localhost:6379/0")

        assert isinstance(
            failed_store,
            auth_security_stores.RedisFailedLoginAttempts,
        )
        assert isinstance(
            pending_store,
            auth_security_stores.RedisPendingMFALogin,
        )

    def test_create_auth_security_stores_rejects_unknown_uri(self):
        """Test unsupported storage URIs are rejected."""
        with pytest.raises(ValueError) as exc_info:
            auth_security_stores.create_auth_security_stores("postgresql://localhost/db")

        assert "Unsupported AUTH_SECURITY_STORAGE_URI" in str(exc_info.value)

    def test_auth_security_uri_falls_back_to_rate_limit(self, monkeypatch):
        """Test auth security URI falls back to rate limit URI."""
        monkeypatch.setattr(
            auth_security_stores.core_config.settings,
            "AUTH_SECURITY_STORAGE_URI",
            None,
        )
        monkeypatch.setattr(
            auth_security_stores.core_config.settings,
            "RATE_LIMIT_STORAGE_URI",
            "redis://localhost:6379/0",
        )

        assert auth_security_stores.get_auth_security_storage_uri() == "redis://localhost:6379/0"

    def test_auth_security_uri_prefers_specific_uri(self, monkeypatch):
        """Test auth-specific URI overrides the rate limit URI."""
        monkeypatch.setattr(
            auth_security_stores.core_config.settings,
            "AUTH_SECURITY_STORAGE_URI",
            "memory://",
        )
        monkeypatch.setattr(
            auth_security_stores.core_config.settings,
            "RATE_LIMIT_STORAGE_URI",
            "redis://localhost:6379/0",
        )

        assert auth_security_stores.get_auth_security_storage_uri() == "memory://"


class TestAuthRouterErrors:
    """Tests for auth router error responses."""

    @pytest.mark.asyncio
    async def test_login_rejects_partial_pkce_params(self):
        """Test login rejects incomplete PKCE query parameters."""
        endpoint = getattr(
            auth_router.login_for_access_token,
            "__wrapped__",
            auth_router.login_for_access_token,
        )

        with pytest.raises(HTTPException) as exc_info:
            await endpoint(
                response=None,
                request=None,
                form_data=SimpleNamespace(
                    username="testuser",
                    password="Password1!",
                ),
                client_type="mobile",
                failed_attempts=object(),
                pending_mfa_store=object(),
                password_hasher=object(),
                token_manager=object(),
                db=object(),
                code_challenge="challenge",
                code_challenge_method=None,
            )

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail == ("code_challenge and code_challenge_method must be provided together")

    @pytest.mark.asyncio
    async def test_mfa_verify_rejects_partial_pkce_params(self):
        """Test MFA verify rejects incomplete PKCE parameters."""
        endpoint = getattr(
            auth_router.verify_mfa_and_login,
            "__wrapped__",
            auth_router.verify_mfa_and_login,
        )

        with pytest.raises(HTTPException) as exc_info:
            await endpoint(
                response=None,
                request=None,
                mfa_request=auth_schema.MFALoginRequest(
                    username="testuser",
                    mfa_code="123456",
                ),
                client_type="mobile",
                failed_attempts=object(),
                pending_mfa_store=object(),
                identity_service=object(),
                password_hasher=object(),
                token_manager=object(),
                db=object(),
                code_challenge=None,
                code_challenge_method="S256",
            )

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail == ("code_challenge and code_challenge_method must be provided together")

    @pytest.mark.asyncio
    async def test_invalid_mfa_response_hides_attempt_count(
        self,
        monkeypatch,
    ):
        """Test invalid MFA response does not disclose counters."""
        raw_username = "Raw.User@example.com"
        log_messages = []

        class PendingMFAStore:
            """Minimal pending MFA store for router testing."""

            def is_locked_out(self, username):
                """Return unlocked for test user."""
                return False

            def get_pending_login(self, username):
                """Return a pending login user ID."""
                return 123

            def claim_pending_login(self, username):
                """Return a claimed pending login user ID."""
                return 123

            def record_failed_attempt(self, username):
                """Return a count that must stay server-side only."""
                return 4

        def capture_log(message, *args, **kwargs):
            """Capture warning log messages for assertions."""
            log_messages.append(message)

        monkeypatch.setattr(
            auth_router.mfa_service,
            "verify_user_mfa",
            lambda *args: False,
        )
        monkeypatch.setattr(
            auth_router.core_logger,
            "print_to_log",
            capture_log,
        )

        endpoint = getattr(
            auth_router.verify_mfa_and_login,
            "__wrapped__",
            auth_router.verify_mfa_and_login,
        )

        with pytest.raises(HTTPException) as exc_info:
            await endpoint(
                response=None,
                request=None,
                mfa_request=auth_schema.MFALoginRequest(
                    username=raw_username,
                    mfa_code="123456",
                ),
                client_type="web",
                failed_attempts=object(),
                pending_mfa_store=PendingMFAStore(),
                identity_service=object(),
                password_hasher=object(),
                token_manager=object(),
                db=object(),
            )

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail == ("Invalid MFA code, backup code or backup code already used.")
        assert "Failed attempts" not in exc_info.value.detail
        assert raw_username not in " ".join(log_messages)
        assert "username_hash=" in " ".join(log_messages)

    @pytest.mark.asyncio
    async def test_valid_mfa_rejects_already_claimed_pending_login(
        self,
        monkeypatch,
    ):
        """Test valid MFA cannot complete if pending login was claimed."""

        class PendingMFAStore:
            """Minimal pending MFA store for claim testing."""

            def is_locked_out(self, username):
                """Return unlocked for test user."""
                return False

            def get_pending_login(self, username):
                """Return a pending login user ID."""
                return 123

            def claim_pending_login(self, username):
                """Simulate another request already claiming the login."""
                return None

        monkeypatch.setattr(
            auth_router.mfa_service,
            "verify_user_mfa",
            lambda *args: True,
        )

        endpoint = getattr(
            auth_router.verify_mfa_and_login,
            "__wrapped__",
            auth_router.verify_mfa_and_login,
        )

        with pytest.raises(HTTPException) as exc_info:
            await endpoint(
                response=None,
                request=None,
                mfa_request=auth_schema.MFALoginRequest(
                    username="testuser",
                    mfa_code="123456",
                ),
                client_type="web",
                failed_attempts=object(),
                pending_mfa_store=PendingMFAStore(),
                identity_service=object(),
                password_hasher=object(),
                token_manager=object(),
                db=object(),
            )

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail == ("No pending MFA login found for this username")


class TestDependencyFunctions:
    """Tests for dependency injection functions."""

    def test_get_pending_mfa_store(self):
        """Test get_pending_mfa_store returns PendingMFALogin instance."""
        store = auth_security_stores.get_pending_mfa_store()
        assert isinstance(
            store,
            (
                auth_security_stores.PendingMFALogin,
                auth_security_stores.RedisPendingMFALogin,
            ),
        )

    def test_get_pending_mfa_store_returns_singleton(self):
        """Test get_pending_mfa_store returns same instance."""
        store1 = auth_security_stores.get_pending_mfa_store()
        store2 = auth_security_stores.get_pending_mfa_store()
        assert store1 is store2

    def test_get_failed_login_attempts(self):
        """Test get_failed_login_attempts returns a store instance."""
        tracker = auth_security_stores.get_failed_login_attempts()
        assert isinstance(
            tracker,
            (
                auth_security_stores.FailedLoginAttempts,
                auth_security_stores.RedisFailedLoginAttempts,
            ),
        )

    def test_get_failed_login_attempts_returns_singleton(self):
        """Test get_failed_login_attempts returns same instance."""
        tracker1 = auth_security_stores.get_failed_login_attempts()
        tracker2 = auth_security_stores.get_failed_login_attempts()
        assert tracker1 is tracker2

    def test_pending_mfa_login_record_attempt_while_locked(self):
        """
        Test that failed attempts don't increment while locked.
        """
        store = auth_security_stores.PendingMFALogin()

        # Record 5 failures to trigger lockout
        for _ in range(5):
            store.record_failed_attempt("testuser")

        # Verify user is locked out
        assert store.is_locked_out("testuser") is True

        # Try to record more failures during lockout
        count1 = store.record_failed_attempt("testuser")
        count2 = store.record_failed_attempt("testuser")

        # Count should not increase
        assert count1 == count2

    def test_failed_login_attempts_record_attempt_while_locked(self):
        """
        Test that failed attempts don't increment while locked.
        """
        store = auth_security_stores.FailedLoginAttempts()

        # Record 5 failures to trigger lockout
        for _ in range(5):
            store.record_failed_attempt("testuser")

        # Verify user is locked out
        assert store.is_locked_out("testuser") is True

        # Try to record more failures during lockout
        count1 = store.record_failed_attempt("testuser")
        count2 = store.record_failed_attempt("testuser")

        # Count should not increase
        assert count1 == count2

    def test_pending_mfa_login_lockout_10_attempts(self):
        """
        Test 30-minute lockout logging after 10 MFA failures.
        """
        store = auth_security_stores.PendingMFALogin()

        # Record 10 failures to trigger 30-min lockout
        for _ in range(10):
            store.record_failed_attempt("testuser")

        # Verify user is locked out
        assert store.is_locked_out("testuser") is True
        lockout_time = store.get_lockout_time("testuser")
        assert lockout_time is not None

    def test_pending_mfa_login_lockout_15_attempts(self):
        """
        Test 2-hour lockout logging after 15 MFA failures.
        """
        store = auth_security_stores.PendingMFALogin()

        # Record 15 failures to trigger 2-hour lockout
        for _ in range(15):
            store.record_failed_attempt("testuser")

        # Verify user is locked out
        assert store.is_locked_out("testuser") is True
        lockout_time = store.get_lockout_time("testuser")
        assert lockout_time is not None

    def test_failed_login_attempts_lockout_10_attempts(self):
        """
        Test 30-minute lockout logging after 10 login failures.
        """
        store = auth_security_stores.FailedLoginAttempts()

        # Record 10 failures to trigger 30-min lockout
        for _ in range(10):
            store.record_failed_attempt("testuser")

        # Verify user is locked out
        assert store.is_locked_out("testuser") is True
        lockout_time = store.get_lockout_time("testuser")
        assert lockout_time is not None

    def test_failed_login_attempts_lockout_20_attempts(self):
        """
        Test 24-hour lockout logging after 20 login failures.
        """
        store = auth_security_stores.FailedLoginAttempts()

        # Record 20 failures to trigger 24-hour lockout
        for _ in range(20):
            store.record_failed_attempt("testuser")

        # Verify user is locked out
        assert store.is_locked_out("testuser") is True
        lockout_time = store.get_lockout_time("testuser")
        assert lockout_time is not None

    def test_pending_mfa_login_lockout_expired_auto_reset(self):
        """Test that expired lockout is automatically reset when checking."""

        store = auth_security_stores.PendingMFALogin()

        # Simulate lockout in the past
        past_time = datetime.now(UTC) - timedelta(hours=1)
        store._lockout._attempts["testuser"] = (5, past_time)

        # Check if locked out - should return False and reset
        assert store.is_locked_out("testuser") is False
        assert "testuser" not in store._lockout._attempts

    def test_failed_login_attempts_lockout_expired_auto_reset(self):
        """Test that expired lockout is automatically reset when checking."""

        store = auth_security_stores.FailedLoginAttempts()

        # Simulate lockout in the past
        past_time = datetime.now(UTC) - timedelta(hours=1)
        store._lockout._attempts["testuser"] = (5, past_time)

        # Check if locked out - should return False and reset
        assert store.is_locked_out("testuser") is False
        assert "testuser" not in store._lockout._attempts

    def test_pending_mfa_get_lockout_time_expired(self):
        """Test get_lockout_time returns None for expired lockouts."""

        store = auth_security_stores.PendingMFALogin()

        # Simulate expired lockout
        past_time = datetime.now(UTC) - timedelta(hours=1)
        store._lockout._attempts["testuser"] = (5, past_time)

        # Should return None for expired lockout
        assert store.get_lockout_time("testuser") is None

    def test_failed_login_attempts_get_lockout_time_expired(self):
        """Test get_lockout_time returns None for expired lockouts."""

        store = auth_security_stores.FailedLoginAttempts()

        # Simulate expired lockout
        past_time = datetime.now(UTC) - timedelta(hours=1)
        store._lockout._attempts["testuser"] = (5, past_time)

        # Should return None for expired lockout
        assert store.get_lockout_time("testuser") is None
