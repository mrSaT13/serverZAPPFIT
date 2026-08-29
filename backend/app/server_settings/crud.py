from typing import overload

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

import core.apprise as core_apprise
import core.cryptography as core_cryptography
import core.decorators as core_decorators
import server_settings.models as server_settings_models
import server_settings.schema as server_settings_schema
import users.users.models as users_models

# Private internal helpers


@overload
def _transform_server_settings(
    server_settings: server_settings_models.ServerSettings,
) -> server_settings_schema.ServerSettingsRead: ...


@overload
def _transform_server_settings(
    server_settings: list[server_settings_models.ServerSettings],
) -> list[server_settings_schema.ServerSettingsRead]: ...


def _transform_server_settings(
    server_settings: server_settings_models.ServerSettings | list[server_settings_models.ServerSettings],
) -> server_settings_schema.ServerSettingsRead | list[server_settings_schema.ServerSettingsRead]:
    """
    Transform a server settings or list of server settings to a Pydantic schema.

     Args:
        server_settings: The server settings ORM instance or list of instances.

     Returns:
        The server settings(s) as a schema.
    """
    if isinstance(server_settings, list):
        return [server_settings_schema.ServerSettingsRead.model_validate(s) for s in server_settings]
    return server_settings_schema.ServerSettingsRead.model_validate(server_settings)


@core_decorators.handle_db_errors
def _get_server_settings_model_or_404(db: Session) -> server_settings_models.ServerSettings:
    """
    Retrieve singleton server settings from database.

    Args:
        db: Database session.

    Returns:
        ServerSettings ORM instance.

    Raises:
        HTTPException: If database error occurs.
    """
    # Get the server settings from the database
    stmt = select(server_settings_models.ServerSettings).where(server_settings_models.ServerSettings.id == 1)
    db_server_settings = db.execute(stmt).scalar_one_or_none()

    if db_server_settings is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Server settings not found.",
        )

    return db_server_settings


# Public CRUD functions


@core_decorators.handle_db_errors
def get_server_settings(db: Session) -> server_settings_schema.ServerSettingsRead | None:
    """
    Retrieve singleton server settings from database.

    Args:
        db: Database session.

    Returns:
        ServerSettingsRead schema or None if not found.

    Raises:
        HTTPException: If database error occurs.
    """
    # Get the server settings from the database
    stmt = select(server_settings_models.ServerSettings).where(server_settings_models.ServerSettings.id == 1)
    db_server_settings = db.execute(stmt).scalar_one_or_none()
    return _transform_server_settings(db_server_settings) if db_server_settings else None


@core_decorators.handle_db_errors
def edit_server_settings(
    server_settings: server_settings_schema.ServerSettingsEdit, db: Session
) -> server_settings_schema.ServerSettingsRead:
    """
    Update server settings in database.

    Args:
        server_settings: New settings to apply.
        db: Database session.

    Returns:
        Updated ServerSettingsRead schema.

    Raises:
        HTTPException: If settings not found or database error.
    """
    # Get the server_settings from the database
    db_server_settings = _get_server_settings_model_or_404(db)

    if server_settings.tileserver_api_key is not None:
        # Encrypt the tile server API key before storing
        if server_settings.tileserver_api_key == "":
            server_settings.tileserver_api_key = None
        elif server_settings.tileserver_api_key:
            encrypted_api_key = core_cryptography.encrypt_token_fernet(server_settings.tileserver_api_key)
            server_settings.tileserver_api_key = encrypted_api_key

    if server_settings.smtp_password is not None:
        if server_settings.smtp_password == "":
            server_settings.smtp_password = None
        elif server_settings.smtp_password:
            server_settings.smtp_password = core_cryptography.encrypt_token_fernet(server_settings.smtp_password)

    # Dictionary of the fields to update if they are not None
    server_settings_data = server_settings.model_dump(exclude_unset=True)
    # Iterate over the fields and update the db_user dynamically
    for key, value in server_settings_data.items():
        setattr(db_server_settings, key, value)

    # Commit the transaction
    db.commit()
    # Refresh the object to ensure it reflects database state
    db.refresh(db_server_settings)

    # Invalidate cached email service so SMTP changes take effect without restart
    try:
        core_apprise.get_email_service.cache_clear()  # type: ignore[attr-defined]
    except Exception:
        pass

    return _transform_server_settings(db_server_settings)


@core_decorators.handle_db_errors
def update_server_settings_login_photo_set(is_set: bool, db: Session) -> None:
    # Get the server_settings from the database
    db_server_settings = _get_server_settings_model_or_404(db)

    db_server_settings.login_photo_set = is_set

    # Commit the transaction
    db.commit()
    # Refresh the object to ensure it reflects database state
    db.refresh(db_server_settings)


@core_decorators.handle_db_errors
def apply_setup_complete(
    payload: server_settings_schema.SetupCompletePayload, db: Session
) -> server_settings_schema.ServerSettingsRead:
    """
    Apply the first-time setup wizard payload and mark the wizard as done.

    The wizard can submit any subset of the editable server settings in a
    single round-trip; this helper applies them, forces
    ``setup_completed=True`` regardless of what the client sent (so the
    wizard cannot be silently re-opened by a tampered request), and returns
    the resulting settings for the front-end to refresh its cache.

    Args:
        payload: Wizard payload containing the new server settings.
        db: Database session.

    Returns:
        The updated :class:`ServerSettingsRead` schema.
    """
    db_server_settings = _get_server_settings_model_or_404(db)

    # Drop server-controlled fields so a client cannot re-open the wizard
    # by sending ``setup_completed=False`` in the payload.
    payload_dict = payload.model_dump(exclude_unset=True)
    payload_dict.pop("id", None)
    payload_dict.pop("setup_completed", None)

    # Encrypt the tile-server API key before persisting it, mirroring the
    # behaviour of the regular edit endpoint.
    raw_api_key = payload_dict.get("tileserver_api_key")
    if raw_api_key:
        payload_dict["tileserver_api_key"] = core_cryptography.encrypt_token_fernet(raw_api_key)
    raw_smtp = payload_dict.get("smtp_password")
    if raw_smtp:
        payload_dict["smtp_password"] = core_cryptography.encrypt_token_fernet(raw_smtp)
    elif raw_smtp == "":
        payload_dict["smtp_password"] = None

    for key, value in payload_dict.items():
        setattr(db_server_settings, key, value)

    # Always flip the wizard flag on success — never trust the client.
    db_server_settings.setup_completed = True

    # Sync the chosen default language to the admin user's profile so the
    # locale sticks across page reloads (applyPreferredLocale reads the
    # user's preferredLanguage, not the server-level defaultLanguage).
    if "default_language" in payload_dict:
        admin_stmt = select(users_models.Users).where(
            users_models.Users.access_type == "admin"
        )
        admin_user = db.execute(admin_stmt).scalar_one_or_none()
        if admin_user is not None:
            admin_user.preferred_language = payload_dict["default_language"]

    db.commit()
    db.refresh(db_server_settings)
    try:
        core_apprise.get_email_service.cache_clear()  # type: ignore[attr-defined]
    except Exception:
        pass
    return _transform_server_settings(db_server_settings)
