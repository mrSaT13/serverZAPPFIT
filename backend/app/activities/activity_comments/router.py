"""API routes for activity comments."""

from collections.abc import Callable
from typing import Annotated

from fastapi import APIRouter, Depends, Security, status
from sqlalchemy.orm import Session

import activities.activity.dependencies as activities_dependencies
import activities.activity_comments.crud as comments_crud
import activities.activity_comments.dependencies as comments_dependencies
import activities.activity_comments.schema as comments_schema
import auth.dependencies as auth_dependencies
import core.database as core_database

router = APIRouter()


@router.get(
    "/activity_id/{activity_id}",
    response_model=list[comments_schema.ActivityComment],
)
async def read_comments(
    activity_id: int,
    _validate_id: Annotated[Callable, Depends(activities_dependencies.validate_activity_id)],
    _check_scopes: Annotated[Callable, Security(auth_dependencies.check_auth_scopes, scopes=["activities:read"])],
    token_user_id: Annotated[int, Depends(auth_dependencies.get_user_id_from_auth)],
    db: Annotated[Session, Depends(core_database.get_db)],
) -> list[comments_schema.ActivityComment]:
    """
    Retrieve all comments for an activity.

    Args:
        activity_id: Activity ID to fetch comments for.
        token_user_id: Authenticated user ID.
        db: Database session.

    Returns:
        List of comments ordered by creation time.
    """
    return comments_crud.get_comments_by_activity_id(activity_id, token_user_id, db)


@router.post(
    "/activity_id/{activity_id}",
    response_model=comments_schema.ActivityComment,
    status_code=status.HTTP_201_CREATED,
)
async def create_comment(
    activity_id: int,
    data: comments_schema.ActivityCommentCreate,
    _validate_id: Annotated[Callable, Depends(activities_dependencies.validate_activity_id)],
    _check_scopes: Annotated[Callable, Security(auth_dependencies.check_auth_scopes, scopes=["activities:write"])],
    token_user_id: Annotated[int, Depends(auth_dependencies.get_user_id_from_auth)],
    db: Annotated[Session, Depends(core_database.get_db)],
) -> comments_schema.ActivityComment:
    """
    Add a comment to an activity.

    Args:
        activity_id: Activity ID to comment on.
        data: Comment content.
        token_user_id: Authenticated user ID.
        db: Database session.

    Returns:
        The newly created comment.
    """
    return comments_crud.create_comment(activity_id, token_user_id, data, db)


@router.put(
    "/{comment_id}",
    response_model=comments_schema.ActivityComment,
)
async def update_comment(
    comment_id: int,
    data: comments_schema.ActivityCommentUpdate,
    _validate_id: Annotated[Callable, Depends(comments_dependencies.validate_comment_id)],
    _check_scopes: Annotated[Callable, Security(auth_dependencies.check_auth_scopes, scopes=["activities:write"])],
    token_user_id: Annotated[int, Depends(auth_dependencies.get_user_id_from_auth)],
    db: Annotated[Session, Depends(core_database.get_db)],
) -> comments_schema.ActivityComment:
    """
    Edit an existing comment (owner only).

    Args:
        comment_id: Comment ID to update.
        data: New comment content.
        token_user_id: Authenticated user ID.
        db: Database session.

    Returns:
        The updated comment.
    """
    return comments_crud.update_comment(comment_id, token_user_id, data, db)


@router.delete(
    "/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
async def delete_comment(
    comment_id: int,
    _validate_id: Annotated[Callable, Depends(comments_dependencies.validate_comment_id)],
    _check_scopes: Annotated[Callable, Security(auth_dependencies.check_auth_scopes, scopes=["activities:write"])],
    token_user_id: Annotated[int, Depends(auth_dependencies.get_user_id_from_auth)],
    db: Annotated[Session, Depends(core_database.get_db)],
) -> None:
    """
    Delete a comment (owner or activity owner).

    Args:
        comment_id: Comment ID to delete.
        token_user_id: Authenticated user ID.
        db: Database session.
    """
    comments_crud.delete_comment(comment_id, token_user_id, db)
