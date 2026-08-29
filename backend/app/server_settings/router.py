import asyncio
from collections.abc import Callable
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    Request,
    Security,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

import auth.dependencies as auth_dependencies
import core.apprise as core_apprise
import core.config as core_config
import core.database as core_database
import core.file_uploads as core_file_uploads
import core.logger as core_logger
import core.scheduler as core_scheduler
import server_settings.crud as server_settings_crud
import server_settings.schema as server_settings_schema
import server_settings.utils as server_settings_utils

# Define the API router
router = APIRouter()


@router.get(
    "",
    response_model=server_settings_schema.ServerSettingsRead,
    status_code=status.HTTP_200_OK,
)
def read_server_settings(
    _check_scopes: Annotated[
        Callable,
        Security(auth_dependencies.check_scopes, scopes=["server_settings:read"]),
    ],
    db: Annotated[
        Session,
        Depends(core_database.get_db),
    ],
) -> server_settings_schema.ServerSettingsRead:
    """
    Get current server settings.

    Requires admin authentication with server_settings:read scope.

    Returns:
        Current server settings configuration with decrypted API key.
    """
    return server_settings_utils.get_server_settings_for_admin(db)


@router.get(
    "/tile_maps_templates",
    response_model=list[server_settings_schema.TileMapsTemplate],
    status_code=status.HTTP_200_OK,
)
def list_tile_maps_templates(
    _check_scopes: Annotated[
        Callable,
        Security(auth_dependencies.check_scopes, scopes=["server_settings:read"]),
    ],
) -> list[server_settings_schema.TileMapsTemplate]:
    """
    Retrieve available tile map templates for server settings.

    This endpoint returns a list of all available tile map templates that can
    be used for configuring map display options in server settings.

    Returns:
        List of tile map template configurations available for the server.

    Raises:
        HTTPException: If the user lacks the required 'server_settings:read'
        scope.
    """
    return server_settings_utils.get_tile_maps_templates()


@router.put(
    "",
    response_model=server_settings_schema.ServerSettingsRead,
    status_code=status.HTTP_200_OK,
)
def edit_server_settings(
    request: Request,
    server_settings_attributes: server_settings_schema.ServerSettingsEdit,
    _check_scopes: Annotated[
        Callable,
        Security(auth_dependencies.check_scopes, scopes=["server_settings:write"]),
    ],
    db: Annotated[
        Session,
        Depends(core_database.get_db),
    ],
) -> server_settings_schema.ServerSettingsRead:
    """
    Update server settings.

    Requires admin authentication with server_settings:write scope.

    Args:
        request: FastAPI request object for accessing app state.
        server_settings_attributes: Settings to update.

    Returns:
        Updated server settings configuration.
    """
    server_settings_updated = server_settings_crud.edit_server_settings(server_settings_attributes, db)

    # Update allowed tile domains in app.state if tileserver_url changed
    if server_settings_attributes.tileserver_url is not None:
        try:
            request.app.state.allowed_tile_domains = server_settings_utils.get_allowed_tile_domains(db)
            core_logger.print_to_log(f"Updated allowed tile domains: {request.app.state.allowed_tile_domains}")
        except Exception as e:
            core_logger.print_to_log(f"Error updating tile domains in app.state: {e}", "error", exc=e)

    # Trigger full thumbnail regeneration if the setting is enabled
    # and any map-related field was part of this update
    _map_fields = {"tileserver_url", "tileserver_api_key", "map_background_color"}
    changed_fields = set(server_settings_attributes.model_dump(exclude_unset=True).keys())
    if server_settings_updated.tileserver_regenerate_thumbnails_on_change and (changed_fields & _map_fields):
        core_logger.print_to_log(
            "Tile server settings changed with regeneration enabled — scheduling thumbnail regeneration",
            "info",
        )
        core_scheduler.schedule_thumbnail_regeneration()

    return server_settings_updated


@router.post(
    "/test-email",
    response_model=dict[str, str],
    status_code=status.HTTP_200_OK,
)
async def test_smtp_email(
    payload: server_settings_schema.TestEmailRequest,
    _check_scopes: Annotated[
        Callable,
        Security(auth_dependencies.check_scopes, scopes=["server_settings:write"]),
    ],
    db: Annotated[
        Session,
        Depends(core_database.get_db),
    ],
) -> dict[str, str]:
    """
    Send a test email via the configured SMTP.

    Uses the DB-stored SMTP settings when present, otherwise env vars.
    Requires ``server_settings:write``. The recipient is supplied in the
    payload so the admin can verify any address (typically their own).
    """
    # Ensure we use fresh DB values (edit already cleared cache, but test may be called standalone)
    try:
        core_apprise.get_email_service.cache_clear()  # type: ignore[attr-defined]
    except Exception:
        pass
    email_service = core_apprise.get_email_service()
    if not email_service.is_smtp_configured():
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="SMTP not configured. Save SMTP settings first.")
    success = await email_service.send_email(
        [payload.to_email],
        subject="ZAPFIT — тестовое письмо",
        html_content="<p>SMTP настроен верно. Это тестовое письмо из ZAPFIT.</p><p>Если вы видите это — сброс пароля и другие уведомления будут работать.</p>",
        text_content="SMTP настроен верно. Тестовое письмо из ZAPFIT.",
    )
    if not success:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Failed to send test email. Check SMTP host/port/credentials and server logs.")
    return {"message": f"Test email sent to {payload.to_email}"}


@router.post(
    "/setup-complete",
    response_model=server_settings_schema.ServerSettingsRead,
    status_code=status.HTTP_200_OK,
)
def complete_setup(
    payload: server_settings_schema.SetupCompletePayload,
    _check_scopes: Annotated[
        Callable,
        Security(auth_dependencies.check_scopes, scopes=["server_settings:write"]),
    ],
    db: Annotated[
        Session,
        Depends(core_database.get_db),
    ],
) -> server_settings_schema.ServerSettingsRead:
    """
    Apply the first-time setup wizard payload and mark the wizard as done.

    Requires admin authentication with ``server_settings:write``. The
    ``setup_completed`` field is intentionally **not** honoured from the
    client: the endpoint always flips it to ``True`` on success so a
    tampered request cannot re-open the wizard.

    Args:
        payload: Wizard payload containing the new server settings.

    Returns:
        The updated server settings.
    """
    return server_settings_crud.apply_setup_complete(payload, db)


@router.post(
    "/upload/login",
    response_model=dict[str, str],
    status_code=status.HTTP_201_CREATED,
)
async def upload_login_photo(
    file: UploadFile,
    _check_scopes: Annotated[
        Callable,
        Security(auth_dependencies.check_scopes, scopes=["server_settings:write"]),
    ],
    db: Annotated[
        Session,
        Depends(core_database.get_db),
    ],
) -> dict[str, str]:
    """
    Upload custom login page photo.

    Requires admin authentication with server_settings:write scope.

    Args:
        file: Image file to upload.

    Returns:
        Full file path where file was saved.
    """
    # Save file using centralized file upload handler
    await core_file_uploads.save_validated_upload(
        file,
        kind=core_file_uploads.UploadKind.IMAGE,
        upload_dir=core_config.SERVER_IMAGES_DIR,
        filename="login.png",
    )

    await asyncio.to_thread(server_settings_crud.update_server_settings_login_photo_set, True, db)

    return {"message": "Login photo uploaded successfully."}


@router.delete(
    "/upload/login",
    response_model=None,
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_login_photo(
    _check_scopes: Annotated[
        Callable,
        Security(auth_dependencies.check_scopes, scopes=["server_settings:write"]),
    ],
    db: Annotated[
        Session,
        Depends(core_database.get_db),
    ],
) -> None:
    """
    Delete custom login page photo.

    Requires admin authentication with server_settings:write scope.

    Returns:
        Success confirmation message.

    Raises:
        HTTPException: If deletion fails.
    """
    await core_file_uploads.delete_files_by_pattern(core_config.SERVER_IMAGES_DIR, "login.png")

    await asyncio.to_thread(server_settings_crud.update_server_settings_login_photo_set, False, db)
