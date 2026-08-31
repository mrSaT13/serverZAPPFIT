import os
import socket
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import cast

from alembic.config import Config

from alembic import command

# Silence stravalib token warnings as early as
# possible: this env var is consulted at import time by
# stravalib, so it must be set before any module that
# transitively imports it runs.
os.environ["SILENCE_TOKEN_WARNINGS"] = "TRUE"

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi.middleware import SlowAPIMiddleware
from starlette.middleware.sessions import SessionMiddleware

from typing import Annotated

from fastapi import Depends, Query, WebSocket, WebSocketDisconnect, WebSocketException
from fastapi import status as fastapi_status

import auth.identity_providers.link_tokens.utils as idp_link_token_utils
import auth.oauth_state.utils as oauth_state_utils
import auth.password_reset_tokens.utils as password_reset_tokens_utils
import auth.sign_up_tokens.utils as sign_up_tokens_utils
import auth.utils as auth_utils
import core.config as core_config
import core.logger as core_logger
import core.middleware as core_middleware
import core.middleware_request_id as core_middleware_request_id
import core.migrations as core_migrations
import core.network as core_network
import core.rate_limit as core_rate_limit
import core.scheduler as core_scheduler
import core.tracing as core_tracing
import garmin.activity_utils as garmin_activity_utils
import garmin.health_utils as garmin_health_utils
import server_settings.schema as server_settings_schema
import server_settings.utils as server_settings_utils
import strava.activity_utils as strava_activity_utils
import strava.utils as strava_utils
from core.database import SessionLocal
from core.database import engine as core_db_engine
from core.routes import router as api_router

_DEPLOYED_ENVIRONMENTS = {"production", "demo"}


def _safe_run[T, **P](
    label: str,
    func: Callable[P, T],
    *args: P.args,
    **kwargs: P.kwargs,
) -> T | None:
    """Invoke a startup task, isolating its failure.

    Logs the exception type (not the raw message, to
    avoid leaking sensitive context) so a single
    misbehaving integration cannot abort backend
    startup.
    """
    try:
        return func(*args, **kwargs)
    except Exception as err:
        core_logger.print_to_log(
            f"Startup task '{label}' failed: {type(err).__name__}",
            "error",
            exc=err,
        )
        return None


async def _safe_run_async[T, **P](
    label: str,
    coro_func: Callable[P, Awaitable[T]],
    *args: P.args,
    **kwargs: P.kwargs,
) -> T | None:
    """Async variant of :func:`_safe_run`."""
    try:
        return await coro_func(*args, **kwargs)
    except Exception as err:
        core_logger.print_to_log(
            f"Startup task '{label}' failed: {type(err).__name__}",
            "error",
            exc=err,
        )
        return None


def _run_alembic_migrations() -> None:
    """Run Alembic upgrade to head.

    Critical: failure here aborts startup because the
    application cannot guarantee schema correctness.
    """
    alembic_cfg = Config("alembic.ini")
    # Disable Alembic's own logger configuration to
    # avoid conflicts with FastAPI / our main logger.
    alembic_cfg.attributes["configure_logger"] = False
    command.upgrade(alembic_cfg, "head")


def _ensure_zapfit_columns() -> None:
    """Add ZAPFIT fitness-metrics columns if they are missing.

    Idempotent: each ADD COLUMN is guarded by an information_schema
    check so it is safe to run on every startup.  This avoids a
    dedicated Alembic migration whose chain position is fragile
    across rebases and Docker-layer caches.
    """
    columns = [
        ("vo2max", "NUMERIC(5,2)"),
        ("tss", "INTEGER"),
        ("hr_tss", "INTEGER"),
        ("trimp", "INTEGER"),
        ("intensity_factor", "NUMERIC(5,3)"),
        ("aerobic_te", "NUMERIC(3,1)"),
        ("anaerobic_te", "NUMERIC(3,1)"),
        ("epoc", "NUMERIC(8,2)"),
        ("suffer_score", "INTEGER"),
        ("efficiency_factor", "NUMERIC(8,4)"),
    ]
    try:
        from sqlalchemy import text

        with SessionLocal() as db:
            for col_name, col_type in columns:
                result = db.execute(
                    text(
                        "SELECT 1 FROM information_schema.columns "
                        "WHERE table_name = 'activities' AND column_name = :col"
                    ),
                    {"col": col_name},
                )
                if result.fetchone() is None:
                    db.execute(text(f"ALTER TABLE activities ADD COLUMN {col_name} {col_type}"))
                    core_logger.print_to_log(f"ZAPFIT: added column activities.{col_name}")
            db.commit()
    except Exception as err:
        core_logger.print_to_log(
            f"ZAPFIT column check failed: {type(err).__name__}",
            "error",
            exc=err,
        )


def _ensure_activity_comments_table() -> None:
    """Create the activity_comments table if it does not exist.

    Idempotent: checks information_schema before creating.
    """
    try:
        from sqlalchemy import text

        with SessionLocal() as db:
            result = db.execute(
                text(
                    "SELECT 1 FROM information_schema.tables "
                    "WHERE table_name = 'activity_comments'"
                )
            )
            if result.fetchone() is None:
                db.execute(text("""
                    CREATE TABLE activity_comments (
                        id SERIAL PRIMARY KEY,
                        activity_id INTEGER NOT NULL REFERENCES activities(id) ON DELETE CASCADE,
                        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                        content TEXT NOT NULL,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
                        updated_at TIMESTAMP WITH TIME ZONE
                    )
                """))
                db.execute(text("CREATE INDEX ix_activity_comments_activity_id ON activity_comments (activity_id)"))
                db.execute(text("CREATE INDEX ix_activity_comments_user_id ON activity_comments (user_id)"))
                db.commit()
                core_logger.print_to_log("ZAPFIT: created table activity_comments")
    except Exception as err:
        core_logger.print_to_log(
            f"ZAPFIT activity_comments table check failed: {type(err).__name__}",
            "error",
            exc=err,
        )


def _refresh_strava_tokens() -> None:
    """Refresh persisted Strava OAuth tokens."""
    strava_utils.refresh_strava_tokens(True)


async def _retrieve_recent_garmin_activities() -> None:
    """Backfill the last day of Garmin Connect activities."""
    await garmin_activity_utils.retrieve_garminconnect_users_activities_for_days(1)


async def _retrieve_recent_strava_activities() -> None:
    """Backfill the last day of Strava activities."""
    await strava_activity_utils.retrieve_strava_users_activities_for_days(
        1,
        True,
    )


async def _retrieve_recent_garmin_health() -> None:
    """Backfill the last day of Garmin Connect health stats."""
    await garmin_health_utils.retrieve_garminconnect_users_health_for_days(1)


def _purge_expired_tokens() -> None:
    """Sweep expired/invalid auth-related tokens from the DB."""
    password_reset_tokens_utils.delete_invalid_tokens_from_db()
    sign_up_tokens_utils.delete_invalid_tokens_from_db()
    oauth_state_utils.delete_expired_oauth_states_from_db()
    idp_link_token_utils.delete_idp_link_expired_tokens_from_db()


def _generate_missing_thumbnails() -> None:
    """Queue map-thumbnail generation for activities missing one.

    Schedules a one-shot job on the background scheduler instead of
    running the (potentially heavy) generation inline, so it cannot
    block lifespan startup and delay the server from accepting
    connections.
    """
    core_scheduler.schedule_missing_thumbnail_generation()


def _init_allowed_tile_domains(fastapi_app: FastAPI) -> None:
    """Populate ``app.state.allowed_tile_domains`` for CSP.

    Falls back to the built-in default provider list if
    the database lookup fails so the application can
    still serve requests with a safe CSP.
    """
    with SessionLocal() as db:
        try:
            fastapi_app.state.allowed_tile_domains = server_settings_utils.get_allowed_tile_domains(db)
            allowed_tile_domains = fastapi_app.state.allowed_tile_domains
            core_logger.print_to_log_and_console(f"Allowed tile domains: {allowed_tile_domains}")
        except Exception as err:
            core_logger.print_to_log(
                f"Error initializing tile domains, using defaults: {type(err).__name__}",
                "error",
                exc=err,
            )
            # Fallback to built-in providers so CSP
            # remains restrictive but functional.
            fastapi_app.state.allowed_tile_domains = server_settings_schema.DEFAULT_ALLOWED_TILE_DOMAINS.copy()


async def _resolve_trusted_proxy_hostnames() -> dict[str, list[str]]:
    """Refresh TRUSTED_PROXIES hostnames at startup.

    Called during Phase 2 of startup (best-effort). The same
    helper is reused by request-time trust checks to avoid stale
    Docker container IPs after proxy-only restarts.

    Returns:
        Dictionary mapping hostnames to their resolved IP lists.
        Empty dict if no hostnames are configured or all fail.
    """
    return core_network.refresh_trusted_proxy_hostnames(
        force=True,
        log_success=True,
    )


async def startup_event(fastapi_app: FastAPI) -> None:
    """Run startup tasks in well-defined phases.

    Phase 1 (critical): schema migrations and the
    background scheduler. Failure aborts startup.

    Phase 2 (best-effort): third-party syncs, token
    purges, thumbnail generation, and CSP tile-domain
    initialisation. Each task is isolated so a single
    failure cannot prevent the backend from serving
    requests.
    """
    core_logger.print_to_log_and_console(f"Backend startup event - {core_config.API_VERSION}")

    # Phase 1: critical pre-flight tasks.
    _run_alembic_migrations()
    _ensure_zapfit_columns()
    _ensure_activity_comments_table()
    await core_migrations.check_migrations()
    core_scheduler.start_scheduler()

    # Phase 2: best-effort background syncs and clean-up.
    core_logger.print_to_log_and_console("Refreshing Strava tokens on startup")
    _safe_run("refresh_strava_tokens", _refresh_strava_tokens)

    core_logger.print_to_log_and_console("Retrieving last day activities from Garmin Connect on startup")
    await _safe_run_async("retrieve_recent_garmin_activities", _retrieve_recent_garmin_activities)

    core_logger.print_to_log_and_console("Retrieving last day activities from Strava on startup")
    await _safe_run_async("retrieve_recent_strava_activities", _retrieve_recent_strava_activities)

    core_logger.print_to_log_and_console("Retrieving last day health stats from Garmin Connect on startup")
    await _safe_run_async(
        "retrieve_recent_garmin_health",
        _retrieve_recent_garmin_health,
    )

    core_logger.print_to_log_and_console("Purging expired tokens (password reset, sign-up, OAuth state, IdP link)")
    _safe_run("purge_expired_tokens", _purge_expired_tokens)

    core_logger.print_to_log_and_console("Scheduling missing activity map thumbnail generation")
    _safe_run("generate_missing_thumbnails", _generate_missing_thumbnails)

    core_logger.print_to_log_and_console("Initializing allowed tile domains for Content Security Policy")
    _init_allowed_tile_domains(fastapi_app)

    core_logger.print_to_log_and_console("Resolving TRUSTED_PROXIES hostnames")
    await _safe_run_async("resolve_trusted_proxy_hostnames", _resolve_trusted_proxy_hostnames)

    core_logger.print_to_log_and_console(f"Allowed trusted proxies: {core_config.settings.TRUSTED_PROXIES}")
    if core_config.settings._resolved_trusted_proxy_ips:
        core_logger.print_to_log_and_console(
            f"Resolved trusted proxy IPs: {sorted(core_config.settings._resolved_trusted_proxy_ips)}",
            "info",
        )


def shutdown_event() -> None:
    """Stop the background scheduler and release DB resources on shutdown."""
    core_logger.print_to_log_and_console("Backend shutdown event")
    core_scheduler.stop_scheduler()

    # Dispose the SQLAlchemy engine so all pooled
    # psycopg connections are closed deterministically.
    try:
        core_db_engine.dispose()
    except Exception as err:
        core_logger.print_to_log_and_console(
            f"Error disposing database engine on shutdown: {type(err).__name__}",
            "error",
        )


@asynccontextmanager
async def lifespan(fastapi_app: FastAPI) -> AsyncIterator[None]:
    """Manage application startup and shutdown."""
    await startup_event(fastapi_app)
    try:
        yield
    finally:
        shutdown_event()


def _dev_lan_origins() -> list[str]:
    """Return ``http://<lan-ip>:<port>`` origins for the frontend dev servers.

    Lets a browser reach the dev frontend/API by plain LAN IP
    (http://192.168.x.x:8080) in addition to localhost and the
    configured domain name. Only used when ENVIRONMENT=development.
    """
    ports = ["8080", "5173", "5174"]
    hosts = {"127.0.0.1"}
    try:
        hostname = socket.gethostname()
        hosts.add(socket.gethostbyname(hostname))
        for info in socket.getaddrinfo(hostname, None):
            addr = info[4][0]
            if ":" not in addr:
                hosts.add(addr)
    except OSError:
        pass
    return [f"http://{host}:{port}" for host in sorted(hosts) for port in ports]


def _build_cors_origins(is_development: bool = False) -> list[str]:
    """Collect the CORS allow-list for the API.

    The base list is the configured domain hosts plus any explicit
    ``CORS_ALLOWED_ORIGINS`` (e.g. plain LAN IPs). Development additionally
    includes localhost and the machine's LAN IPs on the frontend/API ports so
    the web app keeps working when opened by IP instead of the domain name.
    """
    origins = [
        core_config.settings.ENDURAIN_HOST,
        core_config.settings.ZAPFIT_HOST,
    ]
    origins.extend(core_config.settings.CORS_ALLOWED_ORIGINS)
    if is_development:
        origins.extend(["http://localhost:8080", "http://localhost:5173", "http://localhost:5174"])
        origins.extend(_dev_lan_origins())
    # De-duplicate while preserving order.
    return list(dict.fromkeys(origin for origin in origins if origin))


def create_app() -> FastAPI:
    """Build, configure, and return the FastAPI app.

    Pre-flight: validate required env vars, ensure data
    directories exist, and configure the main logger so
    every subsequent log line is captured by the
    environment-appropriate handler.
    """
    # Pre-flight checks that must run before the app is
    # constructed: required environment variables and
    # filesystem layout. Logger setup must happen after
    # config validation so log routing reflects the
    # validated settings.
    core_config.check_required_env_vars()
    core_config.check_required_dirs()
    core_logger.setup_main_logger()

    is_development = core_config.settings.ENVIRONMENT == "development"
    is_deployed = core_config.settings.ENVIRONMENT in _DEPLOYED_ENVIRONMENTS
    docs_url = f"{core_config.ROOT_PATH}/docs" if is_development else None
    redoc_url = f"{core_config.ROOT_PATH}/redoc" if is_development else None

    # Define the FastAPI object
    fastapi_app = FastAPI(
        lifespan=lifespan,
        docs_url=docs_url,
        redoc_url=redoc_url,
        title="ZAPFIT",
        summary="ZAPFIT API — a self-hosted endurance activity tracker forked from Endurain.",
        version=core_config.API_VERSION,
        license_info={
            "name": core_config.LICENSE_NAME,
            "identifier": core_config.LICENSE_IDENTIFIER,
            "url": core_config.LICENSE_URL,
        },
        # OpenAPI tag carrying the fork-acknowledgement string surfaced in
        # ``/docs`` and ``/redoc`` (development only).
        openapi_tags=[
            {
                "name": "fork_acknowledgement",
                "description": (
                    "ZAPFIT is an independent fork of the Endurain project "
                    "(https://github.com/Endurain/Endurain). Thanks to the "
                    "original authors for the foundation this project builds on."
                ),
            },
        ],
    )

    # Add session middleware for OAuth state management
    fastapi_app.add_middleware(
        SessionMiddleware,
        secret_key=cast(str, core_config.read_secret("SECRET_KEY")),
        session_cookie="zapfit_session",
        max_age=3600,  # 1 hour session timeout
        same_site="lax",
        https_only=is_deployed,
    )

    # Add CORS middleware to allow requests from the frontend (domain hosts,
    # explicit CORS_ALLOWED_ORIGINS, plus localhost/LAN IPs in development).
    cors_allow_origins = _build_cors_origins(is_development)

    fastapi_app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_allow_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=[
            "Authorization",
            "Content-Type",
            "X-Client-Type",
            "X-CSRF-Token",
            "X-API-Key",
        ],
        expose_headers=["X-Request-ID"],
        max_age=600,
    )

    # Add security headers middleware (before CSRF for proper header ordering)
    fastapi_app.add_middleware(core_middleware.SecurityHeadersMiddleware)

    # Add CSRF protection middleware
    fastapi_app.add_middleware(core_middleware.CSRFMiddleware)

    # Add rate limiting
    fastapi_app.state.limiter = core_rate_limit.limiter
    fastapi_app.add_exception_handler(
        core_rate_limit.RateLimitExceeded,
        core_rate_limit.rate_limit_exceeded_handler,  # type: ignore[arg-type]
    )
    fastapi_app.add_exception_handler(
        auth_utils.ClearRefreshTokenCookieHTTPException,
        auth_utils.clear_refresh_token_cookie_exception_handler,  # type: ignore[arg-type]
    )
    fastapi_app.add_middleware(SlowAPIMiddleware)

    # RequestIdMiddleware is added last so it executes
    # first in the request chain, ensuring every log
    # line (including those from other middlewares and
    # error responses) carries an X-Request-ID.
    fastapi_app.add_middleware(
        core_middleware_request_id.RequestIdMiddleware,
    )

    # Static mounts must be registered before the
    # catch-all frontend route included by api_router.
    fastapi_app.mount(
        f"/{core_config.USER_IMAGES_URL_PATH}",
        StaticFiles(directory=core_config.USER_IMAGES_DIR),
        name="user_images",
    )
    fastapi_app.mount(
        f"/{core_config.SERVER_IMAGES_URL_PATH}",
        StaticFiles(directory=core_config.SERVER_IMAGES_DIR),
        name="server_images",
    )
    fastapi_app.mount(
        "/activity_media",
        StaticFiles(directory=core_config.settings.ACTIVITY_MEDIA_DIR),
        name="activity_media",
    )
    fastapi_app.mount(
        "/activity_thumbnails",
        StaticFiles(directory=core_config.settings.ACTIVITY_THUMBNAILS_DIR),
        name="activity_thumbnails",
    )
    fastapi_app.mount(
        "/gear_images",
        StaticFiles(directory=core_config.settings.GEAR_IMAGES_DIR),
        name="gear_images",
    )

    # Router files
    fastapi_app.include_router(api_router)

    # Fallback WebSocket route at /ws for clients that skip the
    # /api/v1 prefix (e.g. some Flutter builds).  The canonical
    # endpoint lives at /api/v1/ws via the websocket router.
    import websocket.manager as ws_manager
    import websocket.ticket_store as ws_ticket_store

    @fastapi_app.websocket("/ws")
    async def _fallback_ws(
        websocket: WebSocket,
        ticket: str = Query(alias="ticket"),
        ticket_store: ws_ticket_store.WsTicketStore | ws_ticket_store.RedisWsTicketStore = Depends(
            ws_ticket_store.get_ws_ticket_store
        ),
        manager: ws_manager.WebSocketManager = Depends(ws_manager.get_websocket_manager),
    ) -> None:
        user_id = ticket_store.consume_ticket(ticket)
        if user_id is None:
            raise WebSocketException(
                code=fastapi_status.WS_1008_POLICY_VIOLATION,
                reason="Invalid or expired ticket",
            )
        await manager.connect(user_id, websocket)
        try:
            while True:
                try:
                    await websocket.receive_json()
                except ValueError:
                    core_logger.print_to_log(f"Received malformed JSON from user {user_id}", "warning")
        except WebSocketDisconnect:
            manager.disconnect(user_id)

    # Setup tracing once the app and its routes are
    # registered so instrumentation can wrap them.
    core_tracing.setup_tracing(fastapi_app)

    return fastapi_app


# Create the FastAPI application
app = create_app()
