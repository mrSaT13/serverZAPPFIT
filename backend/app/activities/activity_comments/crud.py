"""CRUD operations for activity comments."""

from datetime import UTC

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

import activities.activity.crud as activity_crud
import activities.activity_comments.models as comment_models
import activities.activity_comments.schema as comment_schema
import core.decorators as core_decorators


@core_decorators.handle_db_errors
def get_comments_by_activity_id(
    activity_id: int,
    token_user_id: int,
    db: Session,
) -> list[comment_models.ActivityComment]:
    """
    Retrieve all comments for an activity.

    The activity must be accessible to the requesting user (owner
    or public/follower visibility).

    Args:
        activity_id: Activity ID to fetch comments for.
        token_user_id: ID of the user making the request.
        db: Database session.

    Returns:
        List of ActivityComment models, ordered by creation time.

    Raises:
        HTTPException: 404 if the activity is not found.
    """
    activity = activity_crud.get_activity_by_id_from_user_id_or_has_visibility(activity_id, token_user_id, db)
    if not activity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Activity not found",
        )

    stmt = (
        select(comment_models.ActivityComment)
        .where(comment_models.ActivityComment.activity_id == activity_id)
        .order_by(comment_models.ActivityComment.created_at.asc())
    )
    return list(db.scalars(stmt).all())


@core_decorators.handle_db_errors
def create_comment(
    activity_id: int,
    user_id: int,
    data: comment_schema.ActivityCommentCreate,
    db: Session,
) -> comment_models.ActivityComment:
    """
    Create a new comment on an activity.

    Args:
        activity_id: Activity ID to comment on.
        user_id: ID of the commenting user.
        data: Comment content.
        db: Database session.

    Returns:
        The newly created ActivityComment.

    Raises:
        HTTPException: 404 if the activity is not found.
    """
    activity = activity_crud.get_activity_by_id_from_user_id_or_has_visibility(activity_id, user_id, db)
    if not activity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Activity not found",
        )

    db_comment = comment_models.ActivityComment(
        activity_id=activity_id,
        user_id=user_id,
        content=data.content,
    )
    db.add(db_comment)
    db.commit()
    db.refresh(db_comment)
    return db_comment


@core_decorators.handle_db_errors
def update_comment(
    comment_id: int,
    user_id: int,
    data: comment_schema.ActivityCommentUpdate,
    db: Session,
) -> comment_models.ActivityComment:
    """
    Update an existing comment (owner only).

    Args:
        comment_id: Comment ID to update.
        user_id: ID of the user attempting the update.
        data: New comment content.
        db: Database session.

    Returns:
        The updated ActivityComment.

    Raises:
        HTTPException: 404 if not found, 403 if not the owner.
    """
    from datetime import datetime

    stmt = select(comment_models.ActivityComment).where(comment_models.ActivityComment.id == comment_id)
    db_comment = db.scalars(stmt).first()

    if not db_comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found",
        )

    if db_comment.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only edit your own comments",
        )

    db_comment.content = data.content
    db_comment.updated_at = datetime.now(UTC)
    db.commit()
    db.refresh(db_comment)
    return db_comment


@core_decorators.handle_db_errors
def delete_comment(
    comment_id: int,
    user_id: int,
    db: Session,
) -> None:
    """
    Delete a comment (owner or activity owner).

    Args:
        comment_id: Comment ID to delete.
        user_id: ID of the user attempting the delete.
        db: Database session.

    Raises:
        HTTPException: 404 if not found, 403 if not authorized.
    """
    stmt = select(comment_models.ActivityComment).where(comment_models.ActivityComment.id == comment_id)
    db_comment = db.scalars(stmt).first()

    if not db_comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Comment not found",
        )

    # Allow if the user is the comment author or the activity owner
    is_comment_author = db_comment.user_id == user_id
    if not is_comment_author:
        activity = activity_crud.get_activity_by_id_from_user_id(db_comment.activity_id, user_id, db)
        if not activity or activity.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to delete this comment",
            )

    db.delete(db_comment)
    db.commit()


@core_decorators.handle_db_errors
def get_comment_count(
    activity_id: int,
    token_user_id: int,
    db: Session,
) -> int:
    """Return the number of comments on an activity.

    Visibility is checked first (same rule as the list endpoint):
    404 when the activity is not accessible.

    Args:
        activity_id: Activity ID to count comments for.
        token_user_id: ID of the user making the request.
        db: Database session.

    Returns:
        Comment count (>= 0).
    """
    activity = activity_crud.get_activity_by_id_from_user_id_or_has_visibility(activity_id, token_user_id, db)
    if not activity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Activity not found",
        )
    stmt = (
        select(func.count())
        .select_from(comment_models.ActivityComment)
        .where(comment_models.ActivityComment.activity_id == activity_id)
    )
    return int(db.scalar(stmt) or 0)


@core_decorators.handle_db_errors
def get_comment_counts(
    activity_ids: list[int],
    token_user_id: int,
    db: Session,
) -> dict[int, int]:
    """Batch comment counts for a feed (one query, no N+1).

    Activities the requester cannot see are silently skipped
    (no count entry), so callers must treat a missing key as 0/hidden.

    Args:
        activity_ids: Activity IDs to count (capped at 100).
        token_user_id: ID of the user making the request.
        db: Database session.

    Returns:
        Mapping activity_id -> count.
    """
    ids = sorted({i for i in activity_ids if isinstance(i, int) and i > 0})[:100]
    if not ids:
        return {}
    stmt = (
        select(
            comment_models.ActivityComment.activity_id,
            func.count(comment_models.ActivityComment.id),
        )
        .where(comment_models.ActivityComment.activity_id.in_(ids))
        .group_by(comment_models.ActivityComment.activity_id)
    )
    rows = db.execute(stmt).all()
    counts: dict[int, int] = {int(aid): int(cnt) for aid, cnt in rows}
    # Visibility filter: drop counts for activities the user cannot see.
    for aid in list(counts.keys()):
        visible = activity_crud.get_activity_by_id_from_user_id_or_has_visibility(aid, token_user_id, db)
        if not visible:
            counts.pop(aid, None)
    return counts
