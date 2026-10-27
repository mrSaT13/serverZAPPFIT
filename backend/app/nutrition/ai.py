"""AI nutrition assistant.

Design:
- Any OpenAI-compatible backend works (OpenAI, OpenRouter, Ollama, vLLM):
  base URL + key + model are server settings managed by the admin
  (server_settings table, key stored Fernet-encrypted).
- The assistant is read-only over the user's own data: it builds a compact
  snapshot (profile, goals, calorie/macro logs, activities, weight, sleep,
  hydration, steps) and answers in the user's language.
- Stateless multi-turn: the client sends recent messages; the server prepends
  the system context.
- Consuming endpoints live in nutrition.router under /ai/*; the admin
  connectivity test lives in server_settings.router (/ai/test).
"""

from dataclasses import dataclass
from datetime import date as date_type, timedelta
from typing import Any

import httpx
from sqlalchemy import func as sa_func, select
from sqlalchemy.orm import Session

import activities.activity.crud as activities_crud
import core.cryptography as core_cryptography
import core.logger as core_logger
import server_settings.models as server_settings_models
import users.users.models as users_models
import users.users_goals.models as users_goals_models
from activities.activity.models import Activity
from health.health_sleep.models import HealthSleep
from health.health_steps.models import HealthSteps
from health.health_water.models import HealthWater
from health.health_weight.models import HealthWeight
from nutrition.models import MealLog
from server_settings.models import ServerSettings

# Ensure every ORM model is registered before any query runs: build_context
# touches Activity, whose relationships (ActivityComment, ActivityMedia, ...)
# only resolve once those classes are imported. Mirrors alembic/env.py and is
# a no-op when the app already imported everything through the routers.
import pathlib as _pathlib
from importlib import import_module as _import_module

_app_dir = _pathlib.Path(__file__).resolve().parents[1]
for _path in sorted(_app_dir.glob("**/models.py")):
    _import_module(".".join(_path.relative_to(_app_dir).with_suffix("").parts))

CHAT_MAX_USER_MESSAGES = 16  # rolled-up window sent to the model
MEAL_SNIPPET_LIMIT = 40  # max product names echoed per day
CONTEXT_WINDOW_DAYS = 14  # nutrition / health snapshot window
ACTIVITY_WINDOW_DAYS = 30  # workout history window
HTTP_TIMEOUT = 60.0


class AiAssistantError(Exception):
    """Raised when the AI provider call fails (network, HTTP, or schema)."""


@dataclass
class AiSettings:
    enabled: bool
    base_url: str | None
    model: str | None
    api_key: str | None  # decrypted

    @property
    def configured(self) -> bool:
        return bool(self.enabled and self.base_url and self.model and self.api_key)


def get_ai_settings(db: Session) -> AiSettings:
    """Load the assistant configuration from server settings (key decrypted)."""
    row = db.scalars(select(ServerSettings).where(ServerSettings.id == 1)).first()
    if not row:
        return AiSettings(enabled=False, base_url=None, model=None, api_key=None)
    api_key = None
    if row.ai_api_key:
        try:
            api_key = core_cryptography.decrypt_token_fernet(row.ai_api_key)
        except Exception as e:
            core_logger.print_to_log(f"AI assistant: failed to decrypt API key: {e}", "error", exc=e)
            api_key = None
    return AiSettings(
        enabled=bool(row.ai_enabled),
        base_url=row.ai_base_url,
        model=row.ai_model,
        api_key=api_key,
    )


async def chat_completion(
    base_url: str,
    api_key: str,
    model: str,
    messages: list[dict[str, str]],
    timeout: float = HTTP_TIMEOUT,
) -> str:
    """Call an OpenAI-compatible /chat/completions endpoint and return the reply text."""
    url = base_url.rstrip("/") + "/chat/completions"
    payload = {"model": model, "messages": messages, "stream": False}
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=payload, headers=headers)
    except Exception as e:
        core_logger.print_to_log(f"AI assistant: request failed: {e}", "error", exc=e)
        raise AiAssistantError(f"AI provider unreachable: {e}") from e

    if response.status_code != 200:
        snippet = response.text[:300]
        core_logger.print_to_log(f"AI assistant: provider returned {response.status_code}: {snippet}", "error")
        if response.status_code in (401, 403):
            raise AiAssistantError("AI provider rejected the credentials (check the API key)")
        if response.status_code == 404:
            raise AiAssistantError("AI provider endpoint not found (check the base URL — it should include /v1)")
        raise AiAssistantError(f"AI provider returned {response.status_code}")

    try:
        data = response.json()
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError, ValueError) as e:
        core_logger.print_to_log(f"AI assistant: unexpected response schema: {e}", "error", exc=e)
        raise AiAssistantError("AI provider returned an unexpected response") from e
    if not content or not str(content).strip():
        raise AiAssistantError("AI provider returned an empty reply")
    return str(content).strip()


def system_prompt(language: str | None) -> str:
    lang = (language or "en").strip() or "en"
    return (
        "You are the built-in nutrition assistant of a self-hosted fitness app (ZAPFIT). "
        "Below is a factual snapshot of ONE user's own data (profile, goals, logged meals, "
        "workouts, weight, sleep, hydration, steps). Use ONLY these facts plus general "
        "nutrition knowledge — never invent numbers that are not in the snapshot, and say "
        "plainly when the data is missing. Answer in the language coded as '"
        + lang
        + "'. Be concise, friendly and practical: short paragraphs or bullet lists, "
        "no medical diagnosis, no extreme dieting advice, remind gently that estimates "
        "are approximate. Do not repeat the raw snapshot back to the user."
    )


def build_context(db: Session, user_id: int, days: int = CONTEXT_WINDOW_DAYS) -> str:
    """Build a compact, factual prompt section for one user (read-only)."""
    user = db.scalars(select(users_models.Users).where(users_models.Users.id == user_id)).first()
    if not user:
        return "User context unavailable."

    today = date_type.today()
    lines: list[str] = [f"Username: {user.username}"]

    # --- demographics ---
    if user.birthdate:
        age = today.year - user.birthdate.year - ((today.month, today.day) < (user.birthdate.month, user.birthdate.day))
        lines.append(f"Demographics: age {age}, gender {user.gender or 'unspecified'}"
                     + (f", height {user.height} cm" if user.height else ""))

    # --- goals ---
    goals = db.scalars(
        select(users_goals_models.UsersGoal).where(users_goals_models.UsersGoal.user_id == user_id)
    ).all()
    for goal in goals:
        parts = [f"interval={goal.interval}"]
        if goal.goal_calories:
            parts.append(f"calories={goal.goal_calories} kcal")
        if goal.goal_distance:
            parts.append(f"distance={goal.goal_distance} km")
        if goal.goal_duration:
            parts.append(f"duration={goal.goal_duration} min")
        if goal.goal_elevation:
            parts.append(f"elevation={goal.goal_elevation} m")
        if goal.goal_activities_number:
            parts.append(f"activities={goal.goal_activities_number} per interval")
        if len(parts) > 1:
            lines.append(f"Goal ({goal.activity_type or 'all activities'}): " + ", ".join(parts))

    # --- nutrition logs: per-day totals over the window ---
    start = today - timedelta(days=days - 1)
    totals_rows = db.execute(
        select(
            MealLog.date,
            sa_func.coalesce(sa_func.sum(MealLog.calories), 0),
            sa_func.coalesce(sa_func.sum(MealLog.protein), 0),
            sa_func.coalesce(sa_func.sum(MealLog.carbs), 0),
            sa_func.coalesce(sa_func.sum(MealLog.fat), 0),
        )
        .where(MealLog.user_id == user_id, MealLog.date >= start)
        .group_by(MealLog.date)
        .order_by(MealLog.date)
    ).all()
    if totals_rows:
        lines.append(f"Logged intake per day (last {days} days, date: kcal / protein_g / carbs_g / fat_g):")
        for row in totals_rows:
            d, cals, prot, carbs, fat = row
            lines.append(f"  {d.isoformat()}: {float(cals):.0f} / {float(prot):.0f} / {float(carbs):.0f} / {float(fat):.0f}")
        recent = _recent_meals(db, user_id, today - timedelta(days=1))
        if recent:
            lines.append(f"Meals logged yesterday ({(today - timedelta(days=1)).isoformat()}): {recent}")
    else:
        lines.append("No meals logged in the last 14 days.")

    # --- workouts (last 30 days) ---
    act_start = today - timedelta(days=ACTIVITY_WINDOW_DAYS)
    acts = db.scalars(
        select(Activity)
        .where(Activity.user_id == user_id, func_date(Activity.start_time) >= act_start)
        .order_by(Activity.start_time.desc())
        .limit(30)
    ).all()
    if acts:
        type_names = _activity_type_names(db, user_id, acts)
        lines.append(f"Recent workouts (last {ACTIVITY_WINDOW_DAYS} days, newest first, date / sport / distance_km / minutes / kcal):")
        for act in acts:
            sport = type_names.get(act.activity_type, str(act.activity_type))
            minutes = round((act.total_timer_time or act.total_elapsed_time or 0) / 60)
            distance_km = round(float(act.distance or 0) / 1000, 2)
            lines.append(
                f"  {act.start_time.date().isoformat()} / {sport} / {distance_km} / {minutes} / {act.calories or 0}"
            )
    else:
        lines.append(f"No workouts recorded in the last {ACTIVITY_WINDOW_DAYS} days.")

    # --- weight trend ---
    weights = db.scalars(
        select(HealthWeight)
        .where(HealthWeight.user_id == user_id, HealthWeight.date >= start)
        .order_by(HealthWeight.date)
    ).all()
    if weights:
        first_w = float(weights[0].weight)
        last_w = float(weights[-1].weight)
        trend = "stable" if abs(last_w - first_w) < 0.3 else ("down" if last_w < first_w else "up")
        lines.append(
            f"Weight: latest {last_w:.1f} kg ({weights[-1].date.isoformat()}), "
            f"{len(weights)} entries in the last {days} days, trend {trend} (was {first_w:.1f} kg)."
        )
    else:
        lines.append("No weight entries in the last 14 days.")

    # --- sleep / hydration / steps averages ---
    _append_average(lines, db, HealthSleep, HealthSleep.total_sleep_seconds, user_id, start,
                    "Sleep", lambda total, n: f"{(total / n / 3600):.1f} h per night")
    _append_average(lines, db, HealthWater, HealthWater.amount_ml, user_id, start,
                    "Hydration", lambda total, n: f"{(total / n / 1000):.2f} l per day")
    _append_average(lines, db, HealthSteps, HealthSteps.steps, user_id, start,
                    "Steps", lambda total, n: f"{(total / n):.0f} per day")

    return "\n".join(lines)


# --- private helpers -------------------------------------------------------


def _recent_meals(db: Session, user_id: int, day: date_type) -> str:
    """One-line listing of the meals logged on a given day."""
    rows = db.scalars(
        select(MealLog).where(MealLog.user_id == user_id, MealLog.date == day).order_by(MealLog.id)
    ).all()
    snippets: list[str] = []
    for row in rows[:MEAL_SNIPPET_LIMIT]:
        kcal = f" {row.calories:.0f} kcal" if row.calories is not None else ""
        grams = f", {row.portion_g:.0f} g" if row.portion_g is not None else ""
        snippets.append(f"{row.meal_type}: {row.product_name}{grams}{kcal}")
    if len(rows) > MEAL_SNIPPET_LIMIT:
        snippets.append(f"… and {len(rows) - MEAL_SNIPPET_LIMIT} more entries")
    return "; ".join(snippets)


def _activity_type_names(db: Session, user_id: int, acts: list[Any]) -> dict[int, str]:
    """Map the activity_type codes present in ``acts`` to human names."""
    try:
        return activities_crud.get_distinct_activity_types_for_user(user_id, db)
    except Exception as e:
        core_logger.print_to_log(f"AI assistant: activity type names unavailable: {e}", "debug")
        return {}


def _append_average(
    lines: list[str],
    db: Session,
    model: type,
    column: Any,
    user_id: int,
    start: date_type,
    label: str,
    format_avg,
) -> None:
    """Append a 'label: average ...' line built from one health metric table."""
    total, count = db.execute(
        select(sa_func.sum(column), sa_func.count()).where(model.user_id == user_id, model.date >= start)
    ).one()
    if count and total:
        lines.append(f"{label}: {format_avg(float(total), int(count))} ({count} entries in the last {CONTEXT_WINDOW_DAYS} days).")


def func_date(column: Any) -> Any:
    """SQLAlchemy cast of a datetime column to date (works on sqlite + postgres)."""
    return sa_func.date(column)
