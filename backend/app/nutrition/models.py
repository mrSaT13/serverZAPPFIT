"""Nutrition ORM models: meal_logs + user wger settings."""

from datetime import date as date_type, datetime as datetime_type

from sqlalchemy import Date, DateTime, ForeignKey, String, Float, Integer
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from core.database import Base


class MealLog(Base):
    __tablename__ = "meal_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    date: Mapped[date_type] = mapped_column(Date, nullable=False, index=True)
    meal_type: Mapped[str] = mapped_column(String(20), nullable=False)  # breakfast/lunch/dinner/snack
    product_name: Mapped[str] = mapped_column(String(250), nullable=False)
    calories: Mapped[float | None] = mapped_column(Float, nullable=True)
    protein: Mapped[float | None] = mapped_column(Float, nullable=True)
    carbs: Mapped[float | None] = mapped_column(Float, nullable=True)
    fat: Mapped[float | None] = mapped_column(Float, nullable=True)
    portion_g: Mapped[float | None] = mapped_column(Float, nullable=True)
    off_barcode: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    created_at: Mapped[datetime_type] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class UserNutritionSettings(Base):
    """Per-user wger sync settings (optional). Disabled by default."""

    __tablename__ = "user_nutrition_settings"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    wger_base_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    wger_api_key: Mapped[str | None] = mapped_column(String(512), nullable=True, comment="Fernet encrypted")
    wger_enabled: Mapped[bool] = mapped_column(default=False, nullable=False)
    updated_at: Mapped[datetime_type] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
