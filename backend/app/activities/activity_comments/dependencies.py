"""Comment ID validation dependency."""

import core.dependencies as core_dependencies


def validate_comment_id(comment_id: int) -> None:
    """
    Validate that comment_id is a non-negative integer.

    Args:
        comment_id: The comment ID to validate.

    Raises:
        HTTPException: If comment_id is less than 0.
    """
    core_dependencies.validate_id(identifier=comment_id, min_value=0, message="Invalid comment ID")
