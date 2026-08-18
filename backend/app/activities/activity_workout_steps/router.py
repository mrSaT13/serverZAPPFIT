"""Activity workout steps router."""

from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends, Security
from sqlalchemy.orm import Session

import activities.activity.dependencies as activities_dependencies
import activities.activity_workout_steps.crud as activity_workout_steps_crud
import activities.activity_workout_steps.schema as activity_workout_steps_schema
import auth.dependencies as auth_dependencies
import core.database as core_database

# Define the API router
router = APIRouter()


@router.get(
    "/activity_id/{activity_id}/all",
    response_model=(list[activity_workout_steps_schema.ActivityWorkoutSteps] | None),
)
async def read_activity_workout_steps_all(
    activity_id: int,
    _validate_id: Annotated[
        Callable,
        Depends(activities_dependencies.validate_activity_id),
    ],
    _check_scopes: Annotated[
        Callable,
        Security(
            auth_dependencies.check_auth_scopes,
            scopes=["activities:read"],
        ),
    ],
    token_user_id: Annotated[
        int,
        Depends(auth_dependencies.get_user_id_from_auth),
    ],
    db: Annotated[
        Session,
        Depends(core_database.get_db),
    ],
):
    """
    Get all workout steps for an activity.

    Returns:
        List of workout steps or None.
    """
    return activity_workout_steps_crud.get_activity_workout_steps(activity_id, token_user_id, db)
