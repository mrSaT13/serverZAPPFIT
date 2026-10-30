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
import notifications.utils as notifications_utils
import websocket.manager as websocket_manager

router = APIRouter()


@router.get(
    "/activity_id/{activity_id}/count",
    response_model=comments_schema.ActivityCommentCount,
)
async def read_comment_count(
    activity_id: int,
    _validate_id: Annotated[Callable, Depends(activities_dependencies.validate_activity_id)],
    _check_scopes: Annotated[Callable, Security(auth_dependencies.check_auth_scopes, scopes=["activities:read"])],
    token_user_id: Annotated[int, Depends(auth_dependencies.get_user_id_from_auth)],
    db: Annotated[Session, Depends(core_database.get_db)],
) -> comments_schema.ActivityCommentCount:
    """Return the comment count for one activity (feed badge)."""
    count = comments_crud.get_comment_count(activity_id, token_user_id, db)
    return comments_schema.ActivityCommentCount(activity_id=activity_id, count=count)


@router.post(
    "/counts",
    response_model=comments_schema.ActivityCommentCountsResponse,
)
async def read_comment_counts(
    data: comments_schema.ActivityCommentCountsRequest,
    _check_scopes: Annotated[Callable, Security(auth_dependencies.check_auth_scopes, scopes=["activities:read"])],
    token_user_id: Annotated[int, Depends(auth_dependencies.get_user_id_from_auth)],
    db: Annotated[Session, Depends(core_database.get_db)],
) -> comments_schema.ActivityCommentCountsResponse:
    """Batch comment counts for visible feed cards (one query)."""
    counts = comments_crud.get_comment_counts(data.activity_ids, token_user_id, db)
    return comments_schema.ActivityCommentCountsResponse(counts={str(k): v for k, v in counts.items()})


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
    ws_manager: Annotated[
        websocket_manager.WebSocketManager,
        Depends(websocket_manager.get_websocket_manager),
    ],
) -> comments_schema.ActivityComment:
    """
    Add a comment to an activity.

    Args:
        activity_id: Activity ID to comment on.
        data: Comment content.
        token_user_id: Authenticated user ID.
        db: Database session.
        ws_manager: WebSocket manager for notifications.

    Returns:
        The newly created comment.
    """
    comment = comments_crud.create_comment(activity_id, token_user_id, data, db)
    # Best-effort owner notification — never fails the 201.
    try:
        activity = comments_crud.activity_crud.get_activity_by_id_from_user_id_or_has_visibility(
            activity_id, token_user_id, db
        )
        owner_id = None
        if activity is not None:
            owner_id = getattr(activity, "user_id", None)
            if owner_id is None and isinstance(activity, dict):
                owner_id = activity.get("user_id")
        if owner_id is not None:
            await notifications_utils.create_new_comment_notification(
                int(owner_id), token_user_id, activity_id, comment.id, ws_manager
            )
    except Exception as err:
        import core.logger as core_logger

        core_logger.print_to_log(f"Comment notification skipped: {err}", "warning")
    return comment


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
