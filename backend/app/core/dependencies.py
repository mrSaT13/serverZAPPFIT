"""Shared validation dependencies for FastAPI routers."""

from typing import Annotated

from fastapi import HTTPException, Query, status


def validate_id(identifier: int, min_value: int, message: str) -> None:
    """
    Validate that an integer identifier is above a minimum.

    Args:
        identifier: Identifier value to validate.
        min_value: Minimum exclusive value.
        message: Error detail for invalid values.

    Returns:
        None.

    Raises:
        HTTPException: If the value is not above the minimum.
    """
    if not (int(identifier) > min_value):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=message,
        )


def validate_type(type_value: int, min_value: int, max_value: int, message: str) -> None:
    """
    Validate that an integer type is inside an inclusive range.

    Args:
        type_value: Type value to validate.
        min_value: Minimum inclusive value.
        max_value: Maximum inclusive value.
        message: Error detail for invalid values.

    Returns:
        None.

    Raises:
        HTTPException: If the value is outside the range.
    """
    if not (min_value <= int(type_value) <= max_value):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=message,
        )


def validate_pagination_values(
    page_number: int,
    num_records: int,
) -> None:
    """
    Validate pagination arguments supplied by callers.

    Args:
        page_number: One-based page number.
        num_records: Number of records per page.

    Returns:
        None.

    Raises:
        HTTPException: If either value is less than one.
    """
    if not (int(page_number) > 0):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Invalid page number, must be higher than 0",
        )

    if not (int(num_records) > 0):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Invalid number of records, must be higher than 0",
        )


def validate_pagination_values_on_query(
    page_number: Annotated[
        int | None,
        Query(description="Pagination page number"),
    ] = None,
    num_records: Annotated[
        int | None,
        Query(description="Number of records per page"),
    ] = None,
) -> None:
    """
    Validate optional pagination query parameters.

    Args:
        page_number: One-based page number, when supplied.
        num_records: Number of records per page, when supplied.

    Returns:
        None.

    Raises:
        HTTPException: If either supplied value is less than one.
    """
    if page_number is None or num_records is None:
        return

    if not (int(page_number) > 0):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Invalid page number, must be higher than 0",
        )

    if not (int(num_records) > 0):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Invalid number of records, must be higher than 0",
        )
