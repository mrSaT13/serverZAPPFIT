from collections.abc import Callable
from datetime import date as datetime_date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Security, status
from sqlalchemy.orm import Session

import auth.dependencies as auth_dependencies
import core.database as core_database
import core.dependencies as core_dependencies
import health.constants as health_constants
import health.health_sleep.crud as health_sleep_crud
import health.health_sleep.schema as health_sleep_schema
import health.health_sleep.sleep_scoring as health_sleep_sleep_scoring

# Define the API router
router = APIRouter()


@router.get(
    "",
    response_model=health_sleep_schema.HealthSleepListResponse,
    status_code=status.HTTP_200_OK,
)
def read_health_sleep_all_pagination(
    _check_scopes: Annotated[Callable, Security(auth_dependencies.check_auth_scopes, scopes=["health:read"])],
    _validate_pagination_values_on_query: Annotated[
        Callable, Depends(core_dependencies.validate_pagination_values_on_query)
    ],
    token_user_id: Annotated[
        int,
        Depends(auth_dependencies.get_user_id_from_auth),
    ],
    db: Annotated[
        Session,
        Depends(core_database.get_db),
    ],
    page_number: Annotated[
        int | None,
        Query(description="Pagination page number"),
    ] = None,
    num_records: Annotated[
        int | None,
        Query(description="Number of records per page"),
    ] = None,
    interval: Annotated[
        health_constants.Interval | None,
        Query(description="Filter by goal interval"),
    ] = None,
) -> health_sleep_schema.HealthSleepListResponse:
    """
    Retrieve health sleep records for the authenticated user.

    This endpoint fetches health sleep data with optional pagination and
    filtering. Access is restricted to users with the 'health:read' scope.

    Args:
        _check_scopes: Security dependency that validates the user has
            'health:read' scope.
        _validate_pagination_values_on_query: Dependency that validates
            pagination parameters.
        token_user_id: The ID of the authenticated user extracted from the
            access token.
        db: Database session for executing queries.
        page_number: Optional pagination page number to retrieve specific page
            of results.
        num_records: Optional number of records per page for pagination.
        interval: Optional filter to retrieve records within a specific goal
            interval.

    Returns:
        HealthSleepListResponse: A response object containing:
            - total: Total count of records matching the filter criteria
            - num_records: Number of records returned per page
            - page_number: Current page number
            - records: List of paginated HealthSleepRead objects
    Raises:
        HTTPException: If the user lacks required 'health:read' scope or if
            pagination values are invalid.
    """
    # Get the total count and records from the database
    total = health_sleep_crud.get_health_sleep_number_by_user_id(token_user_id, db, interval)
    records = health_sleep_crud.get_health_sleep_by_user_id(token_user_id, db, page_number, num_records, interval)

    # Pydantic will convert ORM models to HealthSleepRead via from_attributes=True
    return health_sleep_schema.HealthSleepListResponse(
        total=total,
        num_records=num_records,
        page_number=page_number,
        records=records,
    )


@router.get(
    "/by_date/{sleep_date}",
    response_model=health_sleep_schema.HealthSleepRead,
    status_code=status.HTTP_200_OK,
)
def read_health_sleep_by_date(
    sleep_date: datetime_date,
    _check_scopes: Annotated[Callable, Security(auth_dependencies.check_auth_scopes, scopes=["health:read"])],
    token_user_id: Annotated[
        int,
        Depends(auth_dependencies.get_user_id_from_auth),
    ],
    db: Annotated[
        Session,
        Depends(core_database.get_db),
    ],
) -> health_sleep_schema.HealthSleepRead:
    """
    Retrieve the sleep record of the authenticated user for one date.

    Args:
        sleep_date: Calendar date of the sleep session (YYYY-MM-DD).
        _check_scopes: Security dependency requiring 'health:read'.
        token_user_id: The ID of the authenticated user.
        db: Database session.

    Returns:
        The sleep record for the date.

    Raises:
        HTTPException: 404 when no record exists for the date.
    """
    record = health_sleep_crud.get_health_sleep_by_date_and_user_id(token_user_id, sleep_date.isoformat(), db)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No sleep record found for date {sleep_date.isoformat()}",
        )
    return record


@router.get(
    "/stats/range",
    response_model=health_sleep_schema.HealthSleepRangeStats,
    status_code=status.HTTP_200_OK,
)
def read_health_sleep_range_stats(
    start_date: Annotated[datetime_date, Query(description="Inclusive range start (YYYY-MM-DD)")],
    end_date: Annotated[datetime_date, Query(description="Inclusive range end (YYYY-MM-DD)")],
    _check_scopes: Annotated[Callable, Security(auth_dependencies.check_auth_scopes, scopes=["health:read"])],
    token_user_id: Annotated[
        int,
        Depends(auth_dependencies.get_user_id_from_auth),
    ],
    db: Annotated[
        Session,
        Depends(core_database.get_db),
    ],
) -> health_sleep_schema.HealthSleepRangeStats:
    """
    Aggregate sleep statistics of the authenticated user over a date range.

    Averages are computed over nights that have a record; missing nights
    are not counted.

    Args:
        start_date: Inclusive range start.
        end_date: Inclusive range end.
        _check_scopes: Security dependency requiring 'health:read'.
        token_user_id: The ID of the authenticated user.
        db: Database session.

    Returns:
        Aggregated statistics for the range.

    Raises:
        HTTPException: 400 when the range is invalid.
    """
    if end_date < start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="end_date must be on or after start_date",
        )
    if (end_date - start_date).days > 366:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Date range must not exceed 366 days",
        )

    records = health_sleep_crud.get_health_sleep_by_user_id_in_range(token_user_id, start_date, end_date, db)

    def _average(values: list[int | None]) -> float | None:
        present = [value for value in values if value is not None]
        if not present:
            return None
        return sum(present) / len(present)

    return health_sleep_schema.HealthSleepRangeStats(
        start_date=start_date,
        end_date=end_date,
        nights=len(records),
        avg_total_sleep_seconds=_average([record.total_sleep_seconds for record in records]),
        avg_deep_sleep_seconds=_average([record.deep_sleep_seconds for record in records]),
        avg_light_sleep_seconds=_average([record.light_sleep_seconds for record in records]),
        avg_rem_sleep_seconds=_average([record.rem_sleep_seconds for record in records]),
        avg_awake_sleep_seconds=_average([record.awake_sleep_seconds for record in records]),
        avg_sleep_score_overall=_average([record.sleep_score_overall for record in records]),
    )


@router.post(
    "",
    response_model=health_sleep_schema.HealthSleepRead,
    status_code=status.HTTP_201_CREATED,
)
def create_health_sleep(
    health_sleep: health_sleep_schema.HealthSleepCreate,
    _check_scopes: Annotated[Callable, Security(auth_dependencies.check_auth_scopes, scopes=["health:write"])],
    token_user_id: Annotated[
        int,
        Depends(auth_dependencies.get_user_id_from_auth),
    ],
    db: Annotated[
        Session,
        Depends(core_database.get_db),
    ],
) -> health_sleep_schema.HealthSleepRead:
    """
    Create or update health sleep data for a user.

    This endpoint creates new health sleep data or updates existing data if an entry
    for the specified date already exists. The operation is determined automatically
    based on whether sleep data exists for the given date.

    Args:
        health_sleep (health_sleep_schema.HealthSleepCreate): The health sleep data to create
            or update, including the date and sleep duration.
        _check_scopes (Callable): Security dependency that verifies the user has
            'health:write' scope.
        token_user_id (int): The ID of the authenticated user extracted from the
            access token.
        db (Session): Database session dependency for database operations.

    Returns:
        health_sleep_schema.HealthSleepRead: The created or updated health sleep data.

    Raises:
        HTTPException: 400 error if the date field is not provided in the request.
    """
    # Calculate sleep scores before saving
    health_sleep_sleep_scoring._calculate_and_set_sleep_scores(health_sleep)

    # Date is guaranteed to be present due to HealthSleepCreate validator
    date_str = health_sleep.date.isoformat()  # type: ignore[union-attr]

    # Check if health_sleep for this date already exists
    sleep_for_date = health_sleep_crud.get_health_sleep_by_date_and_user_id(token_user_id, date_str, db)

    if sleep_for_date:
        # Convert to update schema with the existing ID and user_id
        health_sleep_update = health_sleep_schema.HealthSleepUpdate(
            id=sleep_for_date.id, user_id=token_user_id, **health_sleep.model_dump()
        )
        # Updates the health_sleep in the database and returns it
        return health_sleep_crud.edit_health_sleep(token_user_id, health_sleep_update, db)
    else:
        # Creates the health_sleep in the database and returns it
        return health_sleep_crud.create_health_sleep(token_user_id, health_sleep, db)


@router.put(
    "",
    response_model=health_sleep_schema.HealthSleepRead,
    status_code=status.HTTP_200_OK,
)
def edit_health_sleep(
    health_sleep: health_sleep_schema.HealthSleepUpdate,
    _check_scopes: Annotated[Callable, Security(auth_dependencies.check_auth_scopes, scopes=["health:write"])],
    token_user_id: Annotated[
        int,
        Depends(auth_dependencies.get_user_id_from_auth),
    ],
    db: Annotated[
        Session,
        Depends(core_database.get_db),
    ],
) -> health_sleep_schema.HealthSleepRead:
    """
    Edit health sleep data for a user.

    This endpoint updates existing health sleep records in the database for the authenticated user.
    Requires 'health:write' scope for authorization.

    Args:
        health_sleep (health_sleep_schema.HealthSleepUpdate): The health sleep data to be updated,
            containing the new values for the health sleep record.
        _check_scopes (Callable): Security dependency that verifies the user has 'health:write'
            scope permission.
        token_user_id (int): The user ID extracted from the JWT access token, used to identify
            the user making the request.
        db (Session): Database session dependency for performing database operations.

    Returns:
        health_sleep_schema.HealthSleepRead: The updated health sleep record with the new values
            as stored in the database.

    Raises:
        HTTPException: May raise various HTTP exceptions if authorization fails, user is not
            found, or database operations fail.
    """
    # Recalculate sleep scores when editing
    health_sleep_sleep_scoring._calculate_and_set_sleep_scores(health_sleep)

    # Updates the health_sleep in the database and returns it
    return health_sleep_crud.edit_health_sleep(token_user_id, health_sleep, db)


@router.delete("/{health_sleep_id}", response_model=None, status_code=status.HTTP_204_NO_CONTENT)
def delete_health_sleep(
    health_sleep_id: int,
    _check_scopes: Annotated[Callable, Security(auth_dependencies.check_auth_scopes, scopes=["health:write"])],
    token_user_id: Annotated[
        int,
        Depends(auth_dependencies.get_user_id_from_auth),
    ],
    db: Annotated[
        Session,
        Depends(core_database.get_db),
    ],
) -> None:
    """
    Delete a health sleep record for the authenticated user.

    This endpoint removes a specific health sleep entry from the database for the user
    identified by the access token. The user must have 'health:write' scope permission.

    Args:
        health_sleep_id (int): The unique identifier of the health sleep record to delete.
        _check_scopes (Callable): Security dependency that verifies the user has 'health:write' scope.
        token_user_id (int): The user ID extracted from the access token.
        db (Session): Database session dependency for executing the delete operation.

    Returns:
        None: This function does not return a value.

    Raises:
        HTTPException: May be raised by dependencies if:
            - The access token is invalid or expired
            - The user lacks required 'health:write' scope
            - The health sleep record doesn't exist or doesn't belong to the user
    """
    # Deletes entry from database
    health_sleep_crud.delete_health_sleep(token_user_id, health_sleep_id, db)
