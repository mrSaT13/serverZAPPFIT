from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends, Security
from sqlalchemy.orm import Session

import activities.activity.dependencies as activities_dependencies
import activities.activity_sets.crud as activity_sets_crud
import activities.activity_sets.schema as activity_sets_schema
import auth.dependencies as auth_dependencies
import core.database as core_database

# Define the API router
router = APIRouter()


@router.get(
    "/activity_id/{activity_id}/all",
    response_model=list[activity_sets_schema.ActivitySetsRead] | None,
)
async def read_activities_sets_for_activity_all(
    activity_id: int,
    validate_id: Annotated[Callable, Depends(activities_dependencies.validate_activity_id)],
    _check_scopes: Annotated[Callable, Security(auth_dependencies.check_auth_scopes, scopes=["activities:read"])],
    token_user_id: Annotated[
        int,
        Depends(auth_dependencies.get_user_id_from_auth),
    ],
    db: Annotated[
        Session,
        Depends(core_database.get_db),
    ],
):
    # Get the activity sets from the database and return them
    return activity_sets_crud.get_activity_sets(activity_id, token_user_id, db)
