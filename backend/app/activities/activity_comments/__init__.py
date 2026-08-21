"""
Activity comments sub-module.

This module provides CRUD operations, schemas, ORM models, and routes
for user comments on activities.

Exports:
    - CRUD: get_comments_by_activity_id, create_comment,
      update_comment, delete_comment
    - Schemas: ActivityComment, ActivityCommentCreate, ActivityCommentUpdate
    - Models: ActivityComment (ORM model)
    - Routers: router
"""

from .crud import create_comment, delete_comment, get_comments_by_activity_id, update_comment
from .models import ActivityComment as ActivityCommentModel
from .schema import ActivityComment, ActivityCommentCreate, ActivityCommentUpdate

__all__ = [
    "ActivityComment",
    "ActivityCommentCreate",
    "ActivityCommentModel",
    "ActivityCommentUpdate",
    "create_comment",
    "delete_comment",
    "get_comments_by_activity_id",
    "update_comment",
]
