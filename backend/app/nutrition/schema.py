"""Schemas for nutrition diary."""

from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, Field, StrictFloat, StrictInt, StrictStr


class MealLogBase(BaseModel):
    date: date
    meal_type: StrictStr = Field(..., pattern="^(breakfast|lunch|dinner|snack)$")
    product_name: StrictStr = Field(..., max_length=250)
    calories: float | None = None
    protein: float | None = None
    carbs: float | None = None
    fat: float | None = None
    portion_g: float | None = None
    off_barcode: StrictStr | None = Field(default=None, max_length=50)

    model_config = ConfigDict(from_attributes=True)


class MealLogCreate(MealLogBase):
    pass


class MealLogUpdate(MealLogBase):
    id: StrictInt


class MealLogRead(MealLogBase):
    id: StrictInt
    user_id: StrictInt
    created_at: datetime | None = None


class MealLogListResponse(BaseModel):
    total: StrictInt
    records: list[MealLogRead]


class OffSearchResult(BaseModel):
    barcode: StrictStr | None = None
    product_name: StrictStr | None = None
    brands: StrictStr | None = None
    calories_100g: float | None = None
    proteins_100g: float | None = None
    carbs_100g: float | None = None
    fat_100g: float | None = None
    image_url: StrictStr | None = None

    model_config = ConfigDict(extra="allow")


class NutritionSummary(BaseModel):
    date: date
    intake_calories: float
    intake_protein: float
    intake_carbs: float
    intake_fat: float
    burned_calories: float | None = None
    net_calories: float | None = None


class WgerSettingsRead(BaseModel):
    wger_base_url: StrictStr | None = None
    wger_enabled: bool = False
    has_api_key: bool = False

    model_config = ConfigDict(from_attributes=True)


class WgerSettingsUpdate(BaseModel):
    wger_base_url: StrictStr | None = Field(default=None, max_length=500)
    wger_api_key: StrictStr | None = Field(default=None, max_length=512)
    wger_enabled: bool = False

    model_config = ConfigDict(from_attributes=True)


class WgerTestRequest(BaseModel):
    wger_base_url: StrictStr = Field(..., max_length=500)
    wger_api_key: StrictStr = Field(..., max_length=512)
