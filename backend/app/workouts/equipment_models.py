"""User training inventory (dumbbells, barbells, machines …) with weights.

The inventory powers the AI planner: the model receives the list so it only
suggests exercises the user can actually perform at home/gym, and it can quote
real weights. Equipment ids reference the exercise catalog's equipment
dictionary (snapshot ``equipment`` list) so the planner can match rows by id.
"""

from datetime import datetime as datetime_type
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class UserEquipment(Base):
    __tablename__ = "user_equipment"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Free-form display name, e.g. "Гантели 10 кг" / "Штанга 20 кг".
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    # Catalog equipment dictionary id (Barbell=1, Dumbbell=3, Kettlebell=10 …);
    # null for items that do not map cleanly (e.g. a pull-up bar at home).
    equipment_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Weight per item in kg (null when not applicable, e.g. a mat).
    weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(6, 2), nullable=True)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    created_at: Mapped[datetime_type] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
