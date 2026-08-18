from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

import core.database as core_database
import server_settings.crud as server_settings_crud
import server_settings.schema as server_settings_schema
import server_settings.utils as server_settings_utils

# Define the API router
router = APIRouter()


@router.get("", response_model=server_settings_schema.ServerSettingsReadPublic)
def read_public_server_settings(
    request: Request,
    response: Response,
    db: Annotated[
        Session,
        Depends(core_database.get_db),
    ],
) -> server_settings_schema.ServerSettingsReadPublic:
    """
    Get public server settings (unauthenticated).

    Protection Mechanisms:
    - Rate limiting: 60 requests per minute per IP (prevents DoS attacks)

    Returns only the public subset of server configuration
    (sensitive signup approval/verification settings excluded).
    Pydantic model filtering automatically excludes sensitive fields.

    Returns:
        Public subset of server configuration.
    """
    return server_settings_utils.get_server_settings_for_public(db)


@router.get(
    "/setup-status",
    response_model=server_settings_schema.SetupStatusPublic,
)
def read_setup_status(
    db: Annotated[
        Session,
        Depends(core_database.get_db),
    ],
) -> server_settings_schema.SetupStatusPublic:
    """
    Return whether the first-time setup wizard still needs to run.

    The endpoint is intentionally lightweight: the public settings endpoint
    already exposes the rest of the configuration, and exposing the raw
    ``setup_completed`` flag alone lets the login page decide whether to
    redirect newly-authenticated administrators to the wizard without
    pulling the whole settings payload.

    Returns:
        Whether the wizard has been completed and the brand name to render.
    """
    settings = server_settings_crud.get_server_settings(db)
    if settings is None:
        # No settings row at all → treat the wizard as still pending.
        return server_settings_schema.SetupStatusPublic(
            setup_completed=False,
            brand_name="ZAPFIT",
        )
    return server_settings_schema.SetupStatusPublic(
        setup_completed=bool(settings.setup_completed),
        brand_name=settings.brand_name or "ZAPFIT",
    )


@router.get(
    "/setup-options",
    response_model=server_settings_schema.SetupOptions,
)
def read_setup_options() -> server_settings_schema.SetupOptions:
    """
    Return the static options rendered by the first-time setup wizard.

    The list is public because the wizard is reachable from the login page
    and must therefore be usable by an unauthenticated visitor; only static,
    non-sensitive choice data is exposed.

    Returns:
        Theme + language options plus the brand name to render.
    """
    return server_settings_utils.get_setup_options()


@router.get(
    "/tile_maps_templates",
    response_model=list[server_settings_schema.TileMapsTemplate],
)
def list_tile_maps_templates(
    request: Request,
    response: Response,
) -> list[server_settings_schema.TileMapsTemplate]:
    """
    Retrieve available tile map templates for server settings (unauthenticated).

    Protection Mechanisms:
    - Rate limiting: 60 requests per minute per IP (prevents DoS attacks)

    This endpoint returns a list of all available tile map templates that can be
    used for configuring map display options in server settings.

    Returns:
        List of tile map template configurations available for the server.
    """
    return server_settings_utils.get_tile_maps_templates()
