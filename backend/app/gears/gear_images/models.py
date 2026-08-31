"""Gear images ORM model."""

from datetime import datetime as datetime_type

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from core.database import Base

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gears.gear.models import Gear


class GearImage(Base):
    """Image attached to a gear (user uploaded or from mobile sync)."""

    __tablename__ = "gear_images"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    gear_id: Mapped[int] = mapped_column(
        ForeignKey("gear.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Gear ID image belongs to",
    )
    image_path: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        unique=True,
        comment="Filesystem path relative to DATA_DIR or absolute",
    )
    created_at: Mapped[datetime_type] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    gear: Mapped["Gear"] = relationship(back_populates="gear_images")
