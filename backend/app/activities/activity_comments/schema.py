"""Pydantic schemas for activity comments."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr


class ActivityCommentCreate(BaseModel):
    """Payload for creating a new comment."""

    model_config = ConfigDict(extra="forbid")

    content: StrictStr = Field(min_length=1, max_length=2000)


class ActivityCommentUpdate(BaseModel):
    """Payload for editing a comment."""

    model_config = ConfigDict(extra="forbid")

    content: StrictStr = Field(min_length=1, max_length=2000)


class ActivityComment(BaseModel):
    """Activity comment response."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    id: StrictInt
    activity_id: StrictInt
    user_id: StrictInt
    content: str
    created_at: datetime
    updated_at: datetime | None = None
