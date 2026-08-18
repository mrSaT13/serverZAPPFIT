"""Authentication security stores for login and MFA lockout."""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from threading import Lock
from typing import NoReturn, Protocol, runtime_checkable
from urllib.parse import unquote

from redis import Redis, RedisError

import core.config as core_config
import core.logger as core_logger
import core.redis as core_redis


class AuthSecurityStoreUnavailableError(RuntimeError):
    """
    Raised when auth security storage cannot be reached.

    Attributes:
        None.
    """


def _raise_store_unavailable(operation: str, err: RedisError) -> NoReturn:
    """
    Raise a sanitized auth security storage exception.

    Args:
        operation: Storage operation that failed.
        err: Redis client exception.

    Raises:
        AuthSecurityStoreUnavailableError: Always raised.
    """
    core_redis.raise_storage_unavailable_as(
        AuthSecurityStoreUnavailableError,
        display_name="auth security storage",
        operation=operation,
        err=err,
    )


def normalize_username_key(username: str) -> str:
    """Normalise a username for security-store keys.

    Lockout counters must key on the same canonical form regardless of
    casing, surrounding whitespace, or URL-encoded variants supplied by
    the client.

    Args:
        username: Raw username string from the request.

    Returns:
        Canonical key suitable for lockout stores.

    Raises:
        None.
    """
    return unquote(username).replace("+", " ").strip().casefold()


def _log_lockout(
    display_name: str,
    duration_label: str,
    username: str,
    failed_count: int,
) -> None:
    """
    Log a progressive lockout event.

    Args:
        display_name: Human-readable store name.
        duration_label: Human-readable lockout duration.
        username: Normalized username being locked out.
        failed_count: Failed attempt count that caused the lockout.

    Returns:
        None.

    Raises:
        None.
    """
    core_logger.print_to_log(
        f"{display_name} lockout ({duration_label}) applied to user "
        f"{username_log_identifier(username)} after {failed_count} "
        "failed attempts",
        "warning",
        context={
            "username_hash": _username_digest(username),
            "failed_attempts": failed_count,
        },
    )


@runtime_checkable
class FailedLoginStore(Protocol):
    """Contract for failed-login lockout stores (memory or Redis).

    Implemented structurally by :class:`FailedLoginAttempts` and
    :class:`RedisFailedLoginAttempts`. Keys are usernames, normalized
    internally by each implementation.
    """

    def is_locked_out(self, username: str) -> bool: ...

    def get_lockout_time(self, username: str) -> datetime | None: ...

    def record_failed_attempt(self, username: str) -> int: ...

    def reset_attempts(self, username: str) -> None: ...

    def clear_all(self) -> None: ...


@runtime_checkable
class PendingMFAStore(Protocol):
    """Contract for pending-MFA login stores (memory or Redis).

    Implemented structurally by :class:`PendingMFALogin` and
    :class:`RedisPendingMFALogin`. Combines pending-login bookkeeping
    with the per-username MFA failure lockout.
    """

    def add_pending_login(self, username: str, user_id: int) -> None: ...

    def get_pending_login(self, username: str) -> int | None: ...

    def claim_pending_login(self, username: str) -> int | None: ...

    def delete_pending_login(self, username: str) -> None: ...

    def has_pending_login(self, username: str) -> bool: ...

    def clear_for_user(self, user_id: int) -> int: ...

    def cleanup_expired(self) -> int: ...

    def is_locked_out(self, username: str) -> bool: ...

    def get_lockout_time(self, username: str) -> datetime | None: ...

    def record_failed_attempt(self, username: str) -> int: ...

    def reset_attempts(self, username: str) -> None: ...

    def clear_all(self) -> None: ...


@runtime_checkable
class StepUpStore(Protocol):
    """Contract for step-up verification lockout stores (memory or Redis).

    Implemented structurally by :class:`StepUpAttempts` and
    :class:`RedisStepUpAttempts`. Keys are stable user identifiers such
    as ``user:{user_id}`` and are not normalized.
    """

    def is_locked_out(self, key: str) -> bool: ...

    def get_lockout_time(self, key: str) -> datetime | None: ...

    def record_failed_attempt(self, key: str) -> int: ...

    def reset_attempts(self, key: str) -> None: ...

    def clear_all(self) -> None: ...


class _InMemoryProgressiveLockout:
    """
    Process-local progressive-lockout counter shared by in-memory stores.

    Mirrors :class:`_RedisProgressiveLockout` so the in-memory and Redis
    variants of each store share the same thresholds, duration labels,
    and lockout semantics. Keys may optionally be normalized (e.g.
    usernames) before storage; step-up keys are already canonical and
    pass through unchanged.

    Attributes:
        _display_name: Human-readable name used in lockout logs.
        _thresholds: Ascending ``(threshold, lockout_seconds, label)``
            tuples; the highest matched threshold wins.
        _normalize_key: Callable applied to every key before storage.
        _attempts: Failed-attempt counters keyed by (normalized) key.
        _lock: Lock guarding ``_attempts``.
    """

    def __init__(
        self,
        display_name: str,
        thresholds: tuple[tuple[int, int, str], ...],
        normalize_key: Callable[[str], str] | None = None,
    ) -> None:
        """
        Initialize the in-memory progressive lockout helper.

        Args:
            display_name: Human-readable name used in lockout logs.
            thresholds: Exactly three ascending
                ``(threshold, lockout_seconds, label)`` tuples.
            normalize_key: Optional key normalizer; identity when None.

        Raises:
            ValueError: When not given exactly three thresholds.
        """
        if len(thresholds) != 3:
            raise ValueError("In-memory lockout requires exactly 3 thresholds")
        self._display_name = display_name
        self._thresholds = thresholds
        self._normalize_key = normalize_key or (lambda key: key)
        self._attempts: dict[str, tuple[int, datetime | None]] = {}
        self._lock = Lock()

    def is_locked_out(self, key: str) -> bool:
        """
        Check whether a key is currently locked out.

        Args:
            key: Raw lockout key (normalized internally).

        Returns:
            True when a non-expired lockout exists.

        Raises:
            None.
        """
        key = self._normalize_key(key)
        with self._lock:
            entry = self._attempts.get(key)
            if entry is None:
                return False

            _, lockout_until = entry
            if lockout_until is None:
                return False

            if datetime.now(UTC) > lockout_until:
                del self._attempts[key]
                return False

            return True

    def get_lockout_time(self, key: str) -> datetime | None:
        """
        Get the current lockout expiry for a key.

        Args:
            key: Raw lockout key (normalized internally).

        Returns:
            Lockout expiry datetime, or None when not locked.

        Raises:
            None.
        """
        key = self._normalize_key(key)
        with self._lock:
            entry = self._attempts.get(key)
            if entry is None:
                return None

            _, lockout_until = entry
            if lockout_until and datetime.now(UTC) <= lockout_until:
                return lockout_until

            return None

    def record_failed_attempt(self, key: str) -> int:
        """
        Record a failed attempt and apply lockout if a threshold is hit.

        While a key is already locked out, the counter is left unchanged
        and the current count is returned, matching the Redis variant.

        Args:
            key: Raw lockout key (normalized internally).

        Returns:
            Current failed-attempt count.

        Raises:
            None.
        """
        now = datetime.now(UTC)
        key = self._normalize_key(key)
        with self._lock:
            entry = self._attempts.get(key)
            if entry is not None:
                failed_count, lockout_until = entry
                if lockout_until and now <= lockout_until:
                    return failed_count
                failed_count += 1
            else:
                failed_count = 1

            lockout_until = None
            duration_label = None
            for threshold, lockout_seconds, label in reversed(self._thresholds):
                if failed_count >= threshold:
                    lockout_until = now + timedelta(seconds=lockout_seconds)
                    duration_label = label
                    break

            self._attempts[key] = (failed_count, lockout_until)

        if duration_label:
            _log_lockout(self._display_name, duration_label, key, failed_count)
        return failed_count

    def reset_attempts(self, key: str) -> None:
        """
        Clear failed attempts and lockout for a key.

        Args:
            key: Raw lockout key (normalized internally).

        Returns:
            None.

        Raises:
            None.
        """
        key = self._normalize_key(key)
        with self._lock:
            self._attempts.pop(key, None)

    def clear_all(self) -> None:
        """
        Clear every failed-attempt record in this lockout counter.

        Args:
            None.

        Returns:
            None.

        Raises:
            None.
        """
        with self._lock:
            self._attempts.clear()


# Progressive-lockout thresholds shared by the in-memory and Redis store
# variants. Each entry is ``(failed_count_threshold, lockout_seconds,
# duration_label)`` in ascending order; the highest matched threshold wins.
_LOGIN_LOCKOUT_THRESHOLDS: tuple[tuple[int, int, str], ...] = (
    (5, 5 * 60, "5 min"),
    (10, 30 * 60, "30 min"),
    (20, 24 * 60 * 60, "24 hours"),
)
_MFA_LOCKOUT_THRESHOLDS: tuple[tuple[int, int, str], ...] = (
    (5, 5 * 60, "5 min"),
    (10, 30 * 60, "30 min"),
    (15, 2 * 60 * 60, "2 hours"),
)
_STEP_UP_LOCKOUT_THRESHOLDS: tuple[tuple[int, int, str], ...] = (
    (5, 5 * 60, "5 min"),
    (10, 30 * 60, "30 min"),
    (15, 2 * 60 * 60, "2 hours"),
)


class PendingMFALogin:
    """
    Manage pending MFA login sessions in process-local memory.

    Attributes:
        PENDING_MFA_TTL_SECONDS: TTL for pending MFA entries.
        _store: Pending MFA entries keyed by normalized username.
        _failed_attempts: Failed MFA attempts keyed by username.
    """

    PENDING_MFA_TTL_SECONDS: int = 300

    def __init__(self) -> None:
        """
        Initialize the in-memory pending-MFA store.

        Args:
            None.

        Returns:
            None.

        Raises:
            None.
        """
        self._store: dict[str, tuple[int, datetime]] = {}
        self._store_lock = Lock()
        self._lockout = _InMemoryProgressiveLockout(
            "MFA",
            _MFA_LOCKOUT_THRESHOLDS,
            normalize_key=normalize_username_key,
        )

    def add_pending_login(self, username: str, user_id: int) -> None:
        """
        Add a pending MFA login entry for a user.

        Args:
            username: Username to add.
            user_id: User ID tied to the pending MFA login.

        Returns:
            None.

        Raises:
            None.
        """
        username = normalize_username_key(username)
        with self._store_lock:
            self._store[username] = (user_id, datetime.now(UTC))

    def get_pending_login(self, username: str) -> int | None:
        """
        Retrieve the user ID for a pending MFA login.

        Args:
            username: Username to look up.

        Returns:
            User ID if a valid pending login exists.

        Raises:
            None.
        """
        username = normalize_username_key(username)
        with self._store_lock:
            entry = self._store.get(username)
            if entry is None:
                return None

            user_id, created_at = entry
            age = (datetime.now(UTC) - created_at).total_seconds()
            if age > self.PENDING_MFA_TTL_SECONDS:
                del self._store[username]

        if age > self.PENDING_MFA_TTL_SECONDS:
            core_logger.print_to_log(
                f"Pending MFA entry for '{username}' expired after {int(age)}s and was evicted.",
                "info",
            )
            return None

        return user_id

    def claim_pending_login(self, username: str) -> int | None:
        """
        Atomically retrieve and remove a pending MFA login.

        Args:
            username: Username to claim.

        Returns:
            User ID if a valid pending login existed.

        Raises:
            None.
        """
        username = normalize_username_key(username)
        with self._store_lock:
            entry = self._store.get(username)
            if entry is None:
                return None

            user_id, created_at = entry
            age = (datetime.now(UTC) - created_at).total_seconds()
            del self._store[username]

        if age > self.PENDING_MFA_TTL_SECONDS:
            core_logger.print_to_log(
                f"Pending MFA entry for '{username}' expired after {int(age)}s and was evicted.",
                "info",
            )
            return None

        return user_id

    def delete_pending_login(self, username: str) -> None:
        """
        Remove the pending MFA login entry for a username.

        Args:
            username: Username whose pending login should be removed.

        Returns:
            None.

        Raises:
            None.
        """
        username = normalize_username_key(username)
        with self._store_lock:
            self._store.pop(username, None)

    def clear_for_user(self, user_id: int) -> int:
        """
        Remove every pending MFA login entry tied to a user ID.

        Used by credential-lifecycle paths (password change, admin
        force-reset, password reset confirm) to invalidate any pre-MFA
        login attempts that may have been started with the now-rotated
        password.

        Args:
            user_id: User ID whose pending MFA entries should be removed.

        Returns:
            Number of pending MFA entries removed.

        Raises:
            None.
        """
        with self._store_lock:
            matching = [username for username, (entry_user_id, _) in self._store.items() if entry_user_id == user_id]
            for username in matching:
                del self._store[username]
        return len(matching)

    def has_pending_login(self, username: str) -> bool:
        """
        Check if username has a valid pending MFA login.

        Args:
            username: Username to check.

        Returns:
            True if a pending MFA login exists.

        Raises:
            None.
        """
        return self.get_pending_login(username) is not None

    def cleanup_expired(self) -> int:
        """
        Evict all expired pending MFA login entries.

        Args:
            None.

        Returns:
            Number of entries removed.

        Raises:
            None.
        """
        now = datetime.now(UTC)
        with self._store_lock:
            expired = [
                username
                for username, (_, created_at) in self._store.items()
                if (now - created_at).total_seconds() > self.PENDING_MFA_TTL_SECONDS
            ]
            for username in expired:
                del self._store[username]
        if expired:
            core_logger.print_to_log(
                f"Cleaned up {len(expired)} expired pending MFA entries.",
                "info",
            )
        return len(expired)

    def is_locked_out(self, username: str) -> bool:
        """
        Check whether a username is currently locked out from MFA.

        Args:
            username: Username to check.

        Returns:
            True if username is currently locked out.

        Raises:
            None.
        """
        return self._lockout.is_locked_out(username)

    def get_lockout_time(self, username: str) -> datetime | None:
        """
        Get lockout expiry time for username.

        Args:
            username: Username to check.

        Returns:
            Lockout expiry datetime if locked out.

        Raises:
            None.
        """
        return self._lockout.get_lockout_time(username)

    def record_failed_attempt(self, username: str) -> int:
        """
        Record a failed MFA attempt.

        Args:
            username: Username that failed MFA verification.

        Returns:
            Number of failed attempts.

        Raises:
            None.
        """
        return self._lockout.record_failed_attempt(username)

    def reset_attempts(self, username: str) -> None:
        """
        Reset failed MFA attempts for a username.

        Args:
            username: Username to reset.

        Returns:
            None.

        Raises:
            None.
        """
        self._lockout.reset_attempts(username)

    def clear_all(self) -> None:
        """
        Clear all pending login and failed MFA attempt records.

        Args:
            None.

        Returns:
            None.

        Raises:
            None.
        """
        with self._store_lock:
            self._store.clear()
        self._lockout.clear_all()


class FailedLoginAttempts:
    """
    Track failed login attempts in process-local memory.

    Attributes:
        _lockout: Process-local progressive lockout counter.
    """

    def __init__(self) -> None:
        """
        Initialize the in-memory failed-login store.

        Args:
            None.

        Returns:
            None.

        Raises:
            None.
        """
        self._lockout = _InMemoryProgressiveLockout(
            "Login",
            _LOGIN_LOCKOUT_THRESHOLDS,
            normalize_key=normalize_username_key,
        )

    def is_locked_out(self, username: str) -> bool:
        """
        Check whether a username is locked out from login.

        Args:
            username: Username to check.

        Returns:
            True if username is currently locked out.

        Raises:
            None.
        """
        return self._lockout.is_locked_out(username)

    def get_lockout_time(self, username: str) -> datetime | None:
        """
        Get lockout expiry time for username.

        Args:
            username: Username to check.

        Returns:
            Lockout expiry datetime if locked out.

        Raises:
            None.
        """
        return self._lockout.get_lockout_time(username)

    def record_failed_attempt(self, username: str) -> int:
        """
        Record a failed login attempt.

        Args:
            username: Username that failed login.

        Returns:
            Number of failed attempts.

        Raises:
            None.
        """
        return self._lockout.record_failed_attempt(username)

    def reset_attempts(self, username: str) -> None:
        """
        Reset failed login attempts for a username.

        Args:
            username: Username to reset.

        Returns:
            None.

        Raises:
            None.
        """
        self._lockout.reset_attempts(username)

    def clear_all(self) -> None:
        """
        Clear all failed attempt records.

        Args:
            None.

        Returns:
            None.

        Raises:
            None.
        """
        self._lockout.clear_all()


_REDIS_AUTH_KEY_PREFIX = "endurain:auth"

_REDIS_RECORD_FAILURE_SCRIPT = """
local lockout_key = KEYS[1]
local attempts_key = KEYS[2]
local now = tonumber(ARGV[1])
local attempts_ttl = tonumber(ARGV[2])
local low_threshold = tonumber(ARGV[3])
local low_lockout = tonumber(ARGV[4])
local mid_threshold = tonumber(ARGV[5])
local mid_lockout = tonumber(ARGV[6])
local high_threshold = tonumber(ARGV[7])
local high_lockout = tonumber(ARGV[8])

local lockout_until = redis.call("GET", lockout_key)
if lockout_until and tonumber(lockout_until) > now then
    local current_count = redis.call("GET", attempts_key)
    return {tonumber(current_count) or 0, tonumber(lockout_until), 0}
end

if lockout_until then
    redis.call("DEL", lockout_key)
end

local count = redis.call("INCR", attempts_key)
redis.call("EXPIRE", attempts_key, attempts_ttl)

local lockout_seconds = 0
if count >= high_threshold then
    lockout_seconds = high_lockout
elseif count >= mid_threshold then
    lockout_seconds = mid_lockout
elseif count >= low_threshold then
    lockout_seconds = low_lockout
end

if lockout_seconds > 0 then
    lockout_until = now + lockout_seconds
    redis.call("SETEX", lockout_key, lockout_seconds, lockout_until)
    return {count, lockout_until, 1}
end

return {count, 0, 0}
"""


def _now_epoch() -> int:
    """
    Get the current UTC epoch timestamp.

    Returns:
        Current UTC epoch timestamp in seconds.

    Raises:
        None.
    """
    return int(datetime.now(UTC).timestamp())


def _datetime_from_epoch(epoch_seconds: int) -> datetime:
    """
    Convert an epoch timestamp to a timezone-aware datetime.

    Args:
        epoch_seconds: Epoch timestamp in seconds.

    Returns:
        Timezone-aware UTC datetime.

    Raises:
        OSError: When the timestamp cannot be converted.
        ValueError: When the timestamp is outside the valid range.
    """
    return datetime.fromtimestamp(epoch_seconds, tz=UTC)


def _username_digest(username: str) -> str:
    """
    Hash a normalized username for Redis key names.

    Args:
        username: Username to normalize and hash.

    Returns:
        SHA-256 digest for use in Redis keys.

    Raises:
        None.
    """
    normalized_username = normalize_username_key(username)
    return core_redis.sha256_key_digest(normalized_username)


def username_log_identifier(username: str) -> str:
    """
    Build a non-reversible username identifier for logs.

    Args:
        username: Username to normalize and hash.

    Returns:
        Log-safe username identifier.

    Raises:
        None.
    """
    return f"username_hash={_username_digest(username)}"


def get_auth_security_storage_uri() -> str:
    """
    Resolve the configured auth security storage URI.

    Returns:
        Explicit auth security URI, or the rate-limit URI when unset.

    Raises:
        None.
    """
    return core_config.settings.resolved_auth_security_storage_uri


class _RedisProgressiveLockout:
    """
    Store progressive lockout counters in Redis.

    Attributes:
        _redis: Redis client used for storage.
        _name: Logical store name used in key prefixes.
        _display_name: Human-readable name used in logs.
        _thresholds: Failed-attempt thresholds and lockout durations.
        _attempts_ttl_seconds: TTL for failed-attempt counters.
    """

    def __init__(
        self,
        redis_client: Redis,
        name: str,
        display_name: str,
        thresholds: tuple[tuple[int, int, str], ...],
        attempts_ttl_seconds: int,
    ) -> None:
        """
        Initialize the Redis progressive lockout helper.

        Args:
            redis_client: Redis client used for storage.
            name: Logical store name used in key prefixes.
            display_name: Human-readable name used in logs.
            thresholds: Failed-attempt thresholds.
            attempts_ttl_seconds: TTL for failed-attempt counters.

        Raises:
            RedisError: When script registration fails.
        """
        if len(thresholds) != 3:
            raise ValueError("Redis lockout requires exactly 3 thresholds")
        self._redis = redis_client
        self._name = name
        self._display_name = display_name
        self._thresholds = thresholds
        self._attempts_ttl_seconds = attempts_ttl_seconds
        self._record_failure = redis_client.register_script(_REDIS_RECORD_FAILURE_SCRIPT)

    def _attempts_key(self, username: str) -> str:
        """
        Build the Redis key for failed-attempt count.

        Args:
            username: Username to key.

        Returns:
            Redis key for the username's failed-attempt count.

        Raises:
            None.
        """
        username_digest = _username_digest(username)
        return f"{_REDIS_AUTH_KEY_PREFIX}:{self._name}:attempts:{username_digest}"

    def _lockout_key(self, username: str) -> str:
        """
        Build the Redis key for lockout expiry.

        Args:
            username: Username to key.

        Returns:
            Redis key for the username's lockout expiry.

        Raises:
            None.
        """
        username_digest = _username_digest(username)
        return f"{_REDIS_AUTH_KEY_PREFIX}:{self._name}:lockout:{username_digest}"

    def _duration_label(self, failed_count: int) -> str:
        """
        Get the configured duration label for a failed count.

        Args:
            failed_count: Current failed-attempt count.

        Returns:
            Human-readable lockout duration label.

        Raises:
            None.
        """
        for threshold, _lockout_seconds, duration_label in reversed(self._thresholds):
            if failed_count >= threshold:
                return duration_label
        return "unknown"

    def is_locked_out(self, username: str) -> bool:
        """
        Check whether a username is currently locked out.

        Args:
            username: Username to check.

        Returns:
            True when a non-expired lockout exists.

        Raises:
            RedisError: When Redis access fails.
        """
        return self.get_lockout_time(username) is not None

    def get_lockout_time(self, username: str) -> datetime | None:
        """
        Get the current lockout expiry for a username.

        Args:
            username: Username to check.

        Returns:
            Lockout expiry datetime, or None when not locked.

        Raises:
            RedisError: When Redis access fails.
        """
        lockout_key = self._lockout_key(username)
        try:
            raw_lockout_until = self._redis.get(lockout_key)
        except RedisError as err:
            _raise_store_unavailable("get lockout time", err)

        if raw_lockout_until is None:
            return None

        try:
            lockout_until = int(raw_lockout_until)
        except (TypeError, ValueError):
            try:
                self._redis.delete(lockout_key)
            except RedisError as err:
                _raise_store_unavailable("delete invalid lockout", err)
            return None

        if lockout_until <= _now_epoch():
            try:
                self._redis.delete(lockout_key)
            except RedisError as err:
                _raise_store_unavailable("delete expired lockout", err)
            return None

        return _datetime_from_epoch(lockout_until)

    def record_failed_attempt(self, username: str) -> int:
        """
        Record a failed attempt and apply lockout if needed.

        Args:
            username: Username that failed verification.

        Returns:
            Current failed-attempt count.

        Raises:
            RedisError: When Redis access fails.
        """
        normalized_username = normalize_username_key(username)
        script_args = [
            str(_now_epoch()),
            str(self._attempts_ttl_seconds),
        ]
        script_args.extend(str(threshold_value) for threshold in self._thresholds for threshold_value in threshold[:2])

        try:
            script_result = self._record_failure(
                keys=[
                    self._lockout_key(normalized_username),
                    self._attempts_key(normalized_username),
                ],
                args=script_args,
            )
        except RedisError as err:
            _raise_store_unavailable("record failed attempt", err)

        failed_count = int(script_result[0])
        created_lockout = bool(int(script_result[2]))

        if created_lockout:
            _log_lockout(
                self._display_name,
                self._duration_label(failed_count),
                normalized_username,
                failed_count,
            )
        return failed_count

    def reset_attempts(self, username: str) -> None:
        """
        Clear failed attempts and lockout for a username.

        Args:
            username: Username to reset.

        Returns:
            None.

        Raises:
            RedisError: When Redis access fails.
        """
        try:
            self._redis.delete(
                self._attempts_key(username),
                self._lockout_key(username),
            )
        except RedisError as err:
            _raise_store_unavailable("reset attempts", err)

    def clear_all(self) -> None:
        """
        Clear all entries for this logical lockout store.

        Args:
            None.

        Returns:
            None.

        Raises:
            RedisError: When Redis access fails.
        """
        key_pattern = f"{_REDIS_AUTH_KEY_PREFIX}:{self._name}:*"
        try:
            core_redis.delete_matching_keys(self._redis, key_pattern)
        except RedisError as err:
            _raise_store_unavailable("clear lockout store", err)


class RedisFailedLoginAttempts:
    """
    Track failed login attempts in Redis.

    Attributes:
        _lockout: Redis-backed progressive lockout helper.
    """

    def __init__(self, redis_client: Redis) -> None:
        """
        Initialize the Redis failed-login store.

        Args:
            redis_client: Redis client used for storage.

        Raises:
            RedisError: When script registration fails.
        """
        self._lockout = _RedisProgressiveLockout(
            redis_client=redis_client,
            name="login",
            display_name="Login",
            thresholds=(
                (5, 5 * 60, "5 min"),
                (10, 30 * 60, "30 min"),
                (20, 24 * 60 * 60, "24 hours"),
            ),
            attempts_ttl_seconds=24 * 60 * 60,
        )

    def is_locked_out(self, username: str) -> bool:
        """
        Check if username is locked out from failed login attempts.

        Args:
            username: Username to check.

        Returns:
            True if username is currently locked out.

        Raises:
            RedisError: When Redis access fails.
        """
        return self._lockout.is_locked_out(username)

    def get_lockout_time(self, username: str) -> datetime | None:
        """
        Get lockout expiry time for username.

        Args:
            username: Username to check.

        Returns:
            Lockout expiry datetime if locked out.

        Raises:
            RedisError: When Redis access fails.
        """
        return self._lockout.get_lockout_time(username)

    def record_failed_attempt(self, username: str) -> int:
        """
        Record a failed login attempt.

        Args:
            username: Username that failed login.

        Returns:
            Number of failed attempts.

        Raises:
            RedisError: When Redis access fails.
        """
        return self._lockout.record_failed_attempt(username)

    def reset_attempts(self, username: str) -> None:
        """
        Clear failed attempts counter on successful login.

        Args:
            username: Username to reset.

        Returns:
            None.

        Raises:
            RedisError: When Redis access fails.
        """
        self._lockout.reset_attempts(username)

    def clear_all(self) -> None:
        """
        Clear all failed attempt records.

        Args:
            None.

        Returns:
            None.

        Raises:
            RedisError: When Redis access fails.
        """
        self._lockout.clear_all()


class RedisPendingMFALogin:
    """
    Manage pending MFA login sessions in Redis.

    Attributes:
        PENDING_MFA_TTL_SECONDS: TTL for pending MFA entries.
        _redis: Redis client used for storage.
        _lockout: Redis-backed progressive lockout helper.
    """

    PENDING_MFA_TTL_SECONDS: int = PendingMFALogin.PENDING_MFA_TTL_SECONDS

    def __init__(self, redis_client: Redis) -> None:
        """
        Initialize the Redis pending-MFA store.

        Args:
            redis_client: Redis client used for storage.

        Raises:
            RedisError: When script registration fails.
        """
        self._redis = redis_client
        self._lockout = _RedisProgressiveLockout(
            redis_client=redis_client,
            name="mfa",
            display_name="MFA",
            thresholds=(
                (5, 5 * 60, "5 min"),
                (10, 30 * 60, "30 min"),
                (15, 2 * 60 * 60, "2 hours"),
            ),
            attempts_ttl_seconds=2 * 60 * 60,
        )

    def _pending_key(self, username: str) -> str:
        """
        Build the Redis key for a pending MFA login.

        Args:
            username: Username to key.

        Returns:
            Redis key for the pending MFA login.

        Raises:
            None.
        """
        username_digest = _username_digest(username)
        return f"{_REDIS_AUTH_KEY_PREFIX}:mfa:pending:{username_digest}"

    def add_pending_login(self, username: str, user_id: int) -> None:
        """
        Add a pending MFA login entry for a user.

        Args:
            username: Username to add.
            user_id: User ID tied to the pending MFA login.

        Returns:
            None.

        Raises:
            RedisError: When Redis access fails.
        """
        try:
            self._redis.set(
                self._pending_key(username),
                str(user_id),
                ex=self.PENDING_MFA_TTL_SECONDS,
            )
        except RedisError as err:
            _raise_store_unavailable("add pending MFA login", err)

    def get_pending_login(self, username: str) -> int | None:
        """
        Retrieve the user ID for a pending MFA login.

        Args:
            username: Username to look up.

        Returns:
            User ID if a valid pending login exists.

        Raises:
            RedisError: When Redis access fails.
        """
        pending_key = self._pending_key(username)
        try:
            raw_user_id = self._redis.get(pending_key)
        except RedisError as err:
            _raise_store_unavailable("get pending MFA login", err)

        if raw_user_id is None:
            return None
        try:
            return int(raw_user_id)
        except (TypeError, ValueError):
            try:
                self._redis.delete(pending_key)
            except RedisError as err:
                _raise_store_unavailable(
                    "delete invalid pending MFA login",
                    err,
                )
            return None

    def claim_pending_login(self, username: str) -> int | None:
        """
        Atomically retrieve and remove a pending MFA login.

        Args:
            username: Username to claim.

        Returns:
            User ID if a valid pending login existed.

        Raises:
            RedisError: When Redis access fails.
        """
        pending_key = self._pending_key(username)
        try:
            raw_user_id = self._redis.getdel(pending_key)
        except RedisError as err:
            _raise_store_unavailable("claim pending MFA login", err)

        if raw_user_id is None:
            return None
        try:
            return int(raw_user_id)
        except (TypeError, ValueError):
            return None

    def delete_pending_login(self, username: str) -> None:
        """
        Remove the pending MFA login entry for a username.

        Args:
            username: Username whose pending login should be removed.

        Returns:
            None.

        Raises:
            RedisError: When Redis access fails.
        """
        try:
            self._redis.delete(self._pending_key(username))
        except RedisError as err:
            _raise_store_unavailable("delete pending MFA login", err)

    def clear_for_user(self, user_id: int) -> int:
        """
        Remove every pending MFA login entry tied to a user ID.

        Scans the pending-MFA key namespace and deletes the entries
        whose stored user ID matches. With the 5-minute TTL the key
        space is small in normal operation.

        Args:
            user_id: User ID whose pending MFA entries should be removed.

        Returns:
            Number of pending MFA entries removed.

        Raises:
            RedisError: When Redis access fails.
        """
        target_value = str(user_id)
        key_pattern = f"{_REDIS_AUTH_KEY_PREFIX}:mfa:pending:*"
        removed = 0
        try:
            for redis_key in self._redis.scan_iter(
                match=key_pattern,
                count=100,
            ):
                stored_value = self._redis.get(redis_key)
                if stored_value == target_value and self._redis.delete(redis_key):
                    removed += 1
        except RedisError as err:
            _raise_store_unavailable(
                "clear pending MFA logins for user",
                err,
            )
        return removed

    def has_pending_login(self, username: str) -> bool:
        """
        Check if username has a valid pending MFA login.

        Args:
            username: Username to check.

        Returns:
            True if a pending MFA login exists.

        Raises:
            RedisError: When Redis access fails.
        """
        return self.get_pending_login(username) is not None

    def cleanup_expired(self) -> int:
        """
        Return zero because Redis expires pending entries by TTL.

        Args:
            None.

        Returns:
            Always zero.

        Raises:
            None.
        """
        return 0

    def is_locked_out(self, username: str) -> bool:
        """
        Check if username is locked out from MFA attempts.

        Args:
            username: Username to check.

        Returns:
            True if username is currently locked out.

        Raises:
            RedisError: When Redis access fails.
        """
        return self._lockout.is_locked_out(username)

    def get_lockout_time(self, username: str) -> datetime | None:
        """
        Get lockout expiry time for username.

        Args:
            username: Username to check.

        Returns:
            Lockout expiry datetime if locked out.

        Raises:
            RedisError: When Redis access fails.
        """
        return self._lockout.get_lockout_time(username)

    def record_failed_attempt(self, username: str) -> int:
        """
        Record a failed MFA attempt.

        Args:
            username: Username that failed MFA verification.

        Returns:
            Number of failed attempts.

        Raises:
            RedisError: When Redis access fails.
        """
        return self._lockout.record_failed_attempt(username)

    def reset_attempts(self, username: str) -> None:
        """
        Reset failed attempt counter after successful MFA.

        Args:
            username: Username to reset.

        Returns:
            None.

        Raises:
            RedisError: When Redis access fails.
        """
        self._lockout.reset_attempts(username)

    def clear_all(self) -> None:
        """
        Clear all pending login and failed MFA attempt records.

        Args:
            None.

        Returns:
            None.

        Raises:
            RedisError: When Redis access fails.
        """
        key_pattern = f"{_REDIS_AUTH_KEY_PREFIX}:mfa:pending:*"
        try:
            core_redis.delete_matching_keys(self._redis, key_pattern)
        except RedisError as err:
            _raise_store_unavailable("clear pending MFA logins", err)
        self._lockout.clear_all()


class StepUpAttempts:
    """
    Track failed step-up verification attempts in process-local memory.

    Keys are stable user identifiers (e.g. ``user:{user_id}``).

    Attributes:
        _lockout: Process-local progressive lockout counter.
    """

    def __init__(self) -> None:
        """
        Initialize the in-memory step-up attempts store.

        Args:
            None.

        Returns:
            None.

        Raises:
            None.
        """
        self._lockout = _InMemoryProgressiveLockout(
            "Step-up",
            _STEP_UP_LOCKOUT_THRESHOLDS,
        )

    def is_locked_out(self, key: str) -> bool:
        """
        Check whether a key is locked out from step-up.

        Args:
            key: Stable user key (e.g. ``user:{user_id}``).

        Returns:
            True if the key is currently locked out.

        Raises:
            None.
        """
        return self._lockout.is_locked_out(key)

    def get_lockout_time(self, key: str) -> datetime | None:
        """
        Get lockout expiry time for a user key.

        Args:
            key: Stable user key.

        Returns:
            Lockout expiry datetime if locked out.

        Raises:
            None.
        """
        return self._lockout.get_lockout_time(key)

    def record_failed_attempt(self, key: str) -> int:
        """
        Record a failed step-up attempt.

        Args:
            key: Stable user key.

        Returns:
            Number of failed attempts.

        Raises:
            None.
        """
        return self._lockout.record_failed_attempt(key)

    def reset_attempts(self, key: str) -> None:
        """
        Reset failed step-up attempts for a user key.

        Args:
            key: Stable user key.

        Returns:
            None.

        Raises:
            None.
        """
        self._lockout.reset_attempts(key)

    def clear_all(self) -> None:
        """
        Clear all failed step-up attempt records.

        Args:
            None.

        Returns:
            None.

        Raises:
            None.
        """
        self._lockout.clear_all()


class RedisStepUpAttempts:
    """
    Track failed step-up verification attempts in Redis.

    Attributes:
        _lockout: Redis-backed progressive lockout helper.
    """

    def __init__(self, redis_client: Redis) -> None:
        """
        Initialize the Redis step-up attempts store.

        Args:
            redis_client: Redis client used for storage.

        Raises:
            RedisError: When script registration fails.
        """
        self._lockout = _RedisProgressiveLockout(
            redis_client=redis_client,
            name="step_up",
            display_name="Step-up",
            thresholds=(
                (5, 5 * 60, "5 min"),
                (10, 30 * 60, "30 min"),
                (15, 2 * 60 * 60, "2 hours"),
            ),
            attempts_ttl_seconds=2 * 60 * 60,
        )

    def is_locked_out(self, key: str) -> bool:
        """
        Check if a key is locked out from step-up attempts.

        Args:
            key: Stable user key (e.g. ``user:{user_id}``).

        Returns:
            True if the key is currently locked out.

        Raises:
            RedisError: When Redis access fails.
        """
        return self._lockout.is_locked_out(key)

    def get_lockout_time(self, key: str) -> datetime | None:
        """
        Get lockout expiry time for a user key.

        Args:
            key: Stable user key.

        Returns:
            Lockout expiry datetime if locked out.

        Raises:
            RedisError: When Redis access fails.
        """
        return self._lockout.get_lockout_time(key)

    def record_failed_attempt(self, key: str) -> int:
        """
        Record a failed step-up attempt.

        Args:
            key: Stable user key.

        Returns:
            Number of failed attempts.

        Raises:
            RedisError: When Redis access fails.
        """
        return self._lockout.record_failed_attempt(key)

    def reset_attempts(self, key: str) -> None:
        """
        Clear failed step-up attempts for a user key.

        Args:
            key: Stable user key.

        Returns:
            None.

        Raises:
            RedisError: When Redis access fails.
        """
        self._lockout.reset_attempts(key)

    def clear_all(self) -> None:
        """
        Clear all failed step-up attempt records.

        Args:
            None.

        Returns:
            None.

        Raises:
            RedisError: When Redis access fails.
        """
        self._lockout.clear_all()


def create_auth_security_stores(
    storage_uri: str,
) -> tuple[FailedLoginStore, PendingMFAStore]:
    """
    Create auth security stores for the configured backend.

    Args:
        storage_uri: Storage URI selecting memory or Redis.

    Returns:
        Failed-login and pending-MFA store instances.

    Raises:
        RuntimeError: When Redis cannot be initialized.
        ValueError: When the storage URI scheme is unsupported.
    """
    return core_redis.select_storage_backend(
        storage_uri,
        purpose="auth security storage",
        scheme_error_label="AUTH_SECURITY_STORAGE_URI",
        memory_factory=lambda: (FailedLoginAttempts(), PendingMFALogin()),
        redis_factory=lambda redis_client: (
            RedisFailedLoginAttempts(redis_client),
            RedisPendingMFALogin(redis_client),
        ),
    )


failed_login_attempts, pending_mfa_store = create_auth_security_stores(get_auth_security_storage_uri())


def get_pending_mfa_store() -> PendingMFAStore:
    """
    Dependency injection for pending MFA storage.

    Returns:
        Global pending MFA store.

    Raises:
        None.
    """
    return pending_mfa_store


def get_failed_login_attempts() -> FailedLoginStore:
    """
    Dependency injection for failed login attempt storage.

    Returns:
        Global failed login attempts tracker.

    Raises:
        None.
    """
    return failed_login_attempts


def cleanup_expired_pending_mfa_logins() -> None:
    """
    Evict all expired pending MFA login entries.

    Returns:
        None.

    Raises:
        None.
    """
    pending_mfa_store.cleanup_expired()


def clear_pending_mfa_for_user(user_id: int) -> int:
    """
    Remove pending MFA login entries for a user across credential changes.

    Called from password-change paths (self-service, admin force-reset,
    password-reset confirm) so that an attacker who already submitted
    the now-rotated password to ``/auth/login`` and is sitting at the
    pending-MFA step cannot still complete the login by also possessing
    the TOTP factor.

    Storage outages are logged and swallowed because the password
    rotation itself must remain successful; pending entries expire
    naturally after their 5-minute TTL.

    Args:
        user_id: User ID whose pending MFA entries should be removed.

    Returns:
        Number of pending MFA entries removed (zero on storage outage).

    Raises:
        None.
    """
    try:
        return pending_mfa_store.clear_for_user(user_id)
    except AuthSecurityStoreUnavailableError as err:
        core_logger.print_to_log(
            "Failed to clear pending MFA entries during password change; entries will expire naturally via TTL",
            "warning",
            exc=err,
        )
        return 0


def _create_step_up_store(storage_uri: str) -> StepUpStore:
    """
    Create a step-up attempts store for the configured backend.

    Args:
        storage_uri: Storage URI selecting memory or Redis.

    Returns:
        Step-up attempts store instance.

    Raises:
        RuntimeError: When Redis cannot be initialized.
        ValueError: When the storage URI scheme is unsupported.
    """
    return core_redis.select_storage_backend(
        storage_uri,
        purpose="auth security storage",
        scheme_error_label="AUTH_SECURITY_STORAGE_URI",
        memory_factory=StepUpAttempts,
        redis_factory=RedisStepUpAttempts,
    )


step_up_attempts: StepUpStore = _create_step_up_store(get_auth_security_storage_uri())


def get_step_up_attempts() -> StepUpStore:
    """
    Dependency injection for step-up attempt tracking.

    Returns:
        Global step-up attempts store.

    Raises:
        None.
    """
    return step_up_attempts
