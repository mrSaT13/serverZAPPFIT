"""Pydantic schemas for gear images."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr


class GearImageBase(BaseModel):
    gear_id: StrictInt = Field(..., ge=1)
    image_path: StrictStr = Field(..., max_length=500)

    model_config = ConfigDict(from_attributes=True)


class GearImageCreate(GearImageBase):
    pass


class GearImageRead(GearImageBase):
    id: StrictInt
    created_at: datetime | None = None
    image_url: StrictStr | None = Field(default=None, description="Public URL for image")


class GearImagesListResponse(BaseModel):
    total: StrictInt
    records: list[GearImageRead]

    model_config = ConfigDict(from_attributes=True)
