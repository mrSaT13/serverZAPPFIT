"""Schemas for strength workouts."""

from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, Field, StrictFloat, StrictInt, StrictStr


class WorkoutExerciseIn(BaseModel):
    """Exercise prescription inside a plan (create/update)."""

    position: StrictInt = Field(..., ge=0)
    day_label: StrictStr | None = Field(default=None, max_length=100)
    name: StrictStr = Field(..., max_length=250)
    muscle_group: StrictStr | None = Field(default=None, max_length=100)
    wger_exercise_id: StrictInt | None = None
    notes: StrictStr | None = Field(default=None, max_length=500)
    target_sets: StrictInt | None = Field(default=None, ge=1)
    target_reps: StrictStr | None = Field(default=None, max_length=50)
    target_weight_kg: StrictFloat | None = Field(default=None, ge=0)
    rest_s: StrictInt | None = Field(default=None, ge=0)

    model_config = ConfigDict(from_attributes=True)


class WorkoutPlanCreate(BaseModel):
    name: StrictStr = Field(..., max_length=250)
    description: StrictStr | None = Field(default=None, max_length=1000)
    exercises: list[WorkoutExerciseIn] = []


class WorkoutPlanUpdate(BaseModel):
    name: StrictStr = Field(..., max_length=250)
    description: StrictStr | None = Field(default=None, max_length=1000)
    # Exercises are replaced wholesale on update.
    exercises: list[WorkoutExerciseIn] = []


class WorkoutPlanExerciseRead(WorkoutExerciseIn):
    id: StrictInt


class WorkoutPlanRead(BaseModel):
    id: StrictInt
    user_id: StrictInt
    name: StrictStr
    description: StrictStr | None = None
    source: StrictStr
    wger_plan_id: StrictInt | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    exercises: list[WorkoutPlanExerciseRead] = []

    model_config = ConfigDict(from_attributes=True)


class WorkoutSetLogIn(BaseModel):
    exercise_name: StrictStr = Field(..., max_length=250)
    wger_exercise_id: StrictInt | None = None
    set_no: StrictInt = Field(..., ge=1)
    weight_kg: StrictFloat | None = Field(default=None, ge=0)
    reps: StrictInt | None = Field(default=None, ge=0)
    rpe: StrictFloat | None = Field(default=None, ge=0, le=10)
    completed: bool = True

    model_config = ConfigDict(from_attributes=True)


class WorkoutSessionCreate(BaseModel):
    date: date
    plan_id: StrictInt | None = None
    duration_min: StrictFloat | None = Field(default=None, ge=0)
    calories: StrictFloat | None = Field(default=None, ge=0)
    comment: StrictStr | None = Field(default=None, max_length=1000)
    sets: list[WorkoutSetLogIn] = []


class WorkoutSetLogRead(WorkoutSetLogIn):
    id: StrictInt
    session_id: StrictInt


class WorkoutSessionRead(BaseModel):
    id: StrictInt
    user_id: StrictInt
    plan_id: StrictInt | None = None
    date: date
    duration_min: StrictFloat | None = None
    calories: StrictFloat | None = None
    comment: StrictStr | None = None
    created_at: datetime | None = None
    sets: list[WorkoutSetLogRead] = []

    model_config = ConfigDict(from_attributes=True)


class ExercisePoint(BaseModel):
    """One logged session point for an exercise (best set that session)."""

    date: date
    best_weight_kg: float | None = None
    best_reps: int | None = None
    est_1rm: float | None = None
    total_volume: float = 0


class ExerciseProgress(BaseModel):
    exercise_name: StrictStr
    wger_exercise_id: StrictInt | None = None
    sessions: StrictInt = 0
    best_weight_kg: float | None = None
    best_est_1rm: float | None = None
    points: list[ExercisePoint] = []


class WgerRoutinePreview(BaseModel):
    wger_id: StrictInt
    name: StrictStr | None = None
    start: date | None = None
    end: date | None = None
    days: StrictInt = 0
    is_template: bool = False
