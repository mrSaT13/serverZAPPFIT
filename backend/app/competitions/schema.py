"""Pydantic schemas for competitions."""

from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictInt, StrictStr

CompetitionStatus = Literal["upcoming", "completed"]


class CompetitionBase(BaseModel):
    """Shared fields of a competition record."""

    name: Annotated[StrictStr, Field(min_length=1, max_length=100)]
    competition_date: date
    distance_km: Annotated[float, Field(gt=0, le=1000)]
    note: Annotated[StrictStr | None, Field(max_length=500)] = None
    status: CompetitionStatus = "upcoming"
    place: StrictInt | None = Field(default=None, ge=1, le=100000)
    total_participants: StrictInt | None = Field(default=None, ge=1, le=100000)
    result_time_s: StrictInt | None = Field(default=None, ge=0, le=3599999)

    model_config = ConfigDict(extra="forbid")


class CompetitionCreate(CompetitionBase):
    """Body for ``POST /competitions``."""


class CompetitionUpdate(CompetitionBase):
    """Body for ``PUT /competitions/{id}``."""


class CompetitionRead(CompetitionBase):
    """Competition as returned by the API."""

    id: StrictInt = Field(..., ge=1)
    user_id: StrictInt = Field(..., ge=1)

    model_config = ConfigDict(from_attributes=True, extra="forbid")


class NextCompetitionRead(BaseModel):
    """Readiness snapshot for ``GET /competitions/next`` (dashboard widget).

    ``competition`` is ``None`` when the user has no upcoming race — the
    widget simply renders nothing instead of getting a 404.
    """

    competition: CompetitionRead | None = None
    days_left: StrictInt = Field(default=0, ge=0)
    # Rolling 28-day average weekly distance (km of all logged activities / 4).
    avg_weekly_km: Annotated[float, Field(ge=0, le=10000)]
    # Weekly distance a race of this length expects (mirror of the mobile
    # client's preparation-tab thresholds).
    required_weekly_km: Annotated[float, Field(ge=0, le=10000)]
    # avg/required clamped to [0, 1] — the widget's progress-bar fraction.
    readiness: Annotated[float, Field(ge=0, le=1)]

    model_config = ConfigDict(extra="forbid")
