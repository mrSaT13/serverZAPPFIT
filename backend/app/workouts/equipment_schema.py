"""Pydantic schemas for the user training inventory."""

from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr


class EquipmentBase(BaseModel):
    """Shared fields of a training-inventory item."""

    name: Annotated[StrictStr, Field(min_length=1, max_length=100)]
    equipment_id: StrictInt | None = Field(default=None, ge=1, description="Catalog equipment dictionary id")
    weight_kg: Decimal | None = Field(default=None, ge=0, le=999.99, description="Weight per item, kg")
    quantity: Annotated[StrictInt, Field(default=1, ge=1, le=999)] = 1

    model_config = ConfigDict(extra="forbid")


class EquipmentCreate(EquipmentBase):
    """Body for ``POST /workouts/equipment``."""


class EquipmentUpdate(EquipmentBase):
    """Body for ``PUT /workouts/equipment/{id}``."""


class EquipmentRead(EquipmentBase):
    """Inventory item as returned by the API."""

    id: StrictInt = Field(..., ge=1)
    user_id: StrictInt = Field(..., ge=1)

    model_config = ConfigDict(from_attributes=True, extra="forbid")
