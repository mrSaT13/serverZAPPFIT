"""SQLAlchemy ORM models for activity comments."""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base

if TYPE_CHECKING:
    from activities.activity.models import Activity


class ActivityComment(Base):
    """A user comment on an activity."""

    __tablename__ = "activity_comments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    activity_id: Mapped[int] = mapped_column(
        ForeignKey("activities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Activity ID the comment belongs to",
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="User ID of the comment author",
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Comment text",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Comment creation timestamp",
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Last edit timestamp",
    )

    activity: Mapped["Activity"] = relationship(back_populates="comments")
