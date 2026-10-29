"""AI workout-plan generator.

Turns a free-text goal ("хочу накачать грудные мышцы") into a ready-to-review
plan draft whose exercises come exclusively from the baked offline catalog.

Design (mirrors ``nutrition/ai.py``):
- Any OpenAI-compatible backend works; base URL + key + model come from the
  admin-managed server settings (same ``get_ai_settings`` as the nutrition
  assistant — one switch for every AI feature).
- The model only ever PROPOSES: it returns strict JSON, the server validates
  every exercise against the catalog (unknown ids are dropped) and returns a
  draft. Nothing is written to the database — the client shows the draft in
  the normal plan editor and the user still saves it themselves.
- To keep prompts small on local models, the catalog excerpt is narrowed to
  the muscle categories the request mentions (keywords in ru/en); when
  nothing matches, the full catalog is sent. Equipment names are always shown
  per entry so the model picks gear the user actually has access to.
"""

import json as json_module
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

import core.logger as core_logger
import nutrition.ai as nutrition_ai
import workouts.exercise_catalog as exercise_catalog
import workouts.schema as workouts_schema

MAX_EXERCISES = 30  # hard cap on AI-proposed rows
MAX_CATALOG_ROWS = 400  # safety cap on the catalog excerpt sent to the model
HTTP_TIMEOUT = 120.0  # plan generation over a full catalog can be slower

SYSTEM_PROMPT_TEMPLATE = (
    "You are the strength-coach module of a self-hosted fitness app (ZAPFIT). "
    "You build one workout plan from a short user request, choosing exercises "
    "ONLY from the numbered catalog list provided in the user message. Rules:\n"
    "1. Pick exercises that match the requested muscles and goal; respect the "
    "equipment shown per catalog entry (never invent equipment). When the "
    "user's inventory is listed, prefer exercises runnable with that inventory "
    "and use its real weights for target_weight_kg when sensible.\n"
    '2. Group exercises into training days with day_label (e.g. "День 1", "День 2" '
    "in the user's language). 3-6 exercises per day, 1-4 days.\n"
    "3. Sensible prescriptions: target_sets 2-5; target_reps as a string like "
    '"8-12" (12-20 for isolation/core, 5-8 for heavy compounds); rest_s 60-180 '
    "(higher for compounds). target_weight_kg stays null unless the user stated "
    "concrete weights.\n"
    "4. wger_exercise_id MUST be an id from the catalog list and name MUST be "
    "that exercise's name from the list, copied verbatim. muscle_group is the "
    "category name from the list.\n"
    "5. Reply with STRICT JSON only — no markdown fences, no commentary:\n"
    '{"name": "<plan name>", "description": "<1-2 sentences>", "exercises": '
    '[{"wger_exercise_id": 123, "name": "<catalog name>", "muscle_group": '
    '"<category>", "day_label": "<day>", "target_sets": 3, "target_reps": "8-12", '
    '"target_weight_kg": null, "rest_s": 90, "notes": "<short tip or null>"}]}\n'
    "6. Write name, description, day_label and notes in the language coded as "
    "'<lang>'. At most " + str(MAX_EXERCISES) + " exercises total."
)

# Equipment ids always available (snapshot dictionary): gym mat + bodyweight —
# any user can train on the floor, so these never disqualify a catalog row.
_ALWAYS_AVAILABLE_EQUIPMENT = {4, 7}

# ru/en keywords that narrow the catalog excerpt to matching categories.
_CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "Chest": ("груд", "chest", "pec", "жим леж"),
    "Back": ("спин", "широч", "back", "lat", "тяга", "подтяг"),
    "Legs": ("ног", "квадриц", "бедр", "ягодиц", "glute", "leg", "присед", "squat"),
    "Arms": ("рук", "бицепс", "трицепс", "arm", "bicep", "tricep"),
    "Shoulders": ("плеч", "дельт", "shoulder", "delt"),
    "Abs": ("пресс", "живот", "кор", "abs", "core"),
    "Calves": ("икр", "голен", "calf", "calves"),
    "Cardio": ("кардио", "cardio", "бег", "выносл", "hiit"),
}


class AiPlanError(Exception):
    """Raised when plan generation fails (provider, reply schema, empty result)."""


def _focus_category_ids(prompt_lower: str, categories: dict[int, str]) -> set[int]:
    """Category ids whose ru/en keywords appear in the request text."""
    ids: set[int] = set()
    for cat_id, cat_name in categories.items():
        keywords = _CATEGORY_KEYWORDS.get(cat_name)
        if keywords and any(word in prompt_lower for word in keywords):
            ids.add(cat_id)
    return ids


def _catalog_rows(db: Session, focus: set[int]) -> list[exercise_catalog.ExerciseCatalog]:
    """Catalog rows, narrowed to the focused categories and capped."""
    stmt = select(exercise_catalog.ExerciseCatalog).order_by(exercise_catalog.ExerciseCatalog.name)
    if focus:
        stmt = stmt.where(exercise_catalog.ExerciseCatalog.category_id.in_(list(focus)))
    stmt = stmt.limit(MAX_CATALOG_ROWS)
    return list(db.scalars(stmt).all())


def localized_name(row: exercise_catalog.ExerciseCatalog, language: str | None) -> str:
    """Catalog name in the request language, English fallback, canonical last."""
    translations = row.translations or {}
    lang = (language or "en").split("-")[0]
    return translations.get(lang, {}).get("name") or translations.get("en", {}).get("name") or row.name


def build_catalog_excerpt(
    db: Session, prompt: str, language: str | None, allowed_equipment: set[int] | None = None
) -> list[str]:
    """Compact numbered catalog lines, narrowed by request keywords.

    Every line: ``<wger_id> | <name> | <category> | <equipment names>``; names
    are resolved in the request language (English fallback) so the model can
    copy recognisable names verbatim. When ``allowed_equipment`` is given
    (user's inventory), only rows fully covered by it are kept — a floor-only
    user never gets offered barbell exercises.
    """
    snapshot = exercise_catalog.load_snapshot()
    categories = {c["id"]: c["name"] for c in snapshot["categories"]}
    equipment = {e["id"]: e["name"] for e in snapshot["equipment"]}

    focus = _focus_category_ids(prompt.lower(), categories)
    rows = _catalog_rows(db, focus)
    if allowed_equipment is not None:
        rows = [r for r in rows if set(r.equipment_ids or []) <= allowed_equipment]

    lang = (language or "en").split("-")[0]
    lines: list[str] = []
    for row in rows:
        name = localized_name(row, lang)
        equip = ", ".join(equipment.get(i, "?") for i in row.equipment_ids or [])
        lines.append(f"{row.wger_id} | {name} | {categories.get(row.category_id, '?')} | {equip}")
    return lines


def user_inventory(db: Session, user_id: int | None) -> list[Any]:
    """The user's training inventory rows (empty when unknown/disabled)."""
    if user_id is None:
        return []
    from sqlalchemy import select

    import workouts.equipment_models as equipment_models

    stmt = (
        select(equipment_models.UserEquipment)
        .where(equipment_models.UserEquipment.user_id == user_id)
        .order_by(equipment_models.UserEquipment.name)
    )
    return list(db.scalars(stmt).all())


def inventory_block(db: Session, user_id: int | None) -> tuple[str, set[int] | None]:
    """Prompt block describing the user's inventory + allowed equipment ids.

    Returns the text to append to the user message and the set of equipment
    ids the catalog should be filtered by (``None`` = no inventory, no filter).
    """
    rows = user_inventory(db, user_id)
    if not rows:
        return "", None
    snapshot = exercise_catalog.load_snapshot()
    equipment = {e["id"]: e["name"] for e in snapshot["equipment"]}

    allowed: set[int] = set(_ALWAYS_AVAILABLE_EQUIPMENT)
    lines: list[str] = []
    for row in rows:
        if row.equipment_id is not None:
            allowed.add(int(row.equipment_id))
        qty = f" x{row.quantity}" if row.quantity and row.quantity > 1 else ""
        weight = f" ({row.weight_kg} kg)" if row.weight_kg is not None else ""
        kind = equipment.get(row.equipment_id) if row.equipment_id is not None else None
        suffix = f" — {kind}" if kind else ""
        lines.append(f"- {row.name}{weight}{qty}{suffix}")
    block = "User's available training inventory (prefer exercises using only these):\n" + "\n".join(lines)
    return block, allowed


def parse_plan_json(text: str) -> dict[str, Any]:
    """Extract the strict-JSON plan object from a model reply.

    Tolerates markdown fences and stray prose around the object.
    """
    cleaned = text.strip()
    if cleaned.startswith("```"):
        first_newline = cleaned.find("\n")
        cleaned = cleaned[first_newline + 1 :] if first_newline != -1 else cleaned
        end = cleaned.rfind("```")
        if end != -1:
            cleaned = cleaned[:end]
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start == -1 or end <= start:
        raise AiPlanError("AI reply contains no JSON object")
    try:
        data = json_module.loads(cleaned[start : end + 1])
    except ValueError as e:
        raise AiPlanError(f"AI reply is not valid JSON: {e}") from e
    if not isinstance(data, dict) or not isinstance(data.get("exercises"), list):
        raise AiPlanError("AI reply JSON misses the exercises list")
    return data


def _clean(value: Any, limit: int) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text[:limit] if text else None


def _to_int(value: Any) -> int | None:
    try:
        n = int(value)
    except (TypeError, ValueError):
        return None
    return n if n >= 0 else None


def _to_float(value: Any) -> float | None:
    try:
        n = float(value)
    except (TypeError, ValueError):
        return None
    return n if n >= 0 else None


def validate_draft(data: dict[str, Any], db: Session, language: str | None) -> workouts_schema.AiPlanDraft:
    """Normalise the parsed JSON into an ``AiPlanDraft``.

    Unknown ``wger_exercise_id`` rows are dropped (the model may hallucinate);
    names are re-resolved from the catalog in the request language. Position is
    derived from the list order — the client re-numbers on save anyway.
    """
    known: dict[int, exercise_catalog.ExerciseCatalog | None] = {}
    exercises: list[workouts_schema.AiPlanDraftExercise] = []
    for raw in data["exercises"]:
        if len(exercises) >= MAX_EXERCISES:
            break
        if not isinstance(raw, dict):
            continue
        wger_id = raw.get("wger_exercise_id")
        try:
            wger_id = int(wger_id) if wger_id is not None else None
        except (TypeError, ValueError):
            wger_id = None
        if wger_id is not None and wger_id not in known:
            known[wger_id] = db.get(exercise_catalog.ExerciseCatalog, wger_id)
        row = known.get(wger_id) if wger_id is not None else None
        if wger_id is not None and row is None:
            continue  # hallucinated id — the exercise is not in the catalog
        name = str(raw.get("name") or "").strip()
        if row is not None:
            name = localized_name(row, language)
        if not name:
            continue  # nothing displayable — skip the row
        exercises.append(
            workouts_schema.AiPlanDraftExercise(
                day_label=_clean(raw.get("day_label"), 100),
                name=name[:250],
                muscle_group=_clean(raw.get("muscle_group"), 100),
                wger_exercise_id=wger_id,
                notes=_clean(raw.get("notes"), 500),
                target_sets=_to_int(raw.get("target_sets")),
                target_reps=_clean(raw.get("target_reps"), 50),
                target_weight_kg=_to_float(raw.get("target_weight_kg")),
                rest_s=_to_int(raw.get("rest_s")),
            )
        )
    if not exercises:
        raise AiPlanError("AI returned no usable exercises")
    return workouts_schema.AiPlanDraft(
        name=_clean(data.get("name"), 250) or "AI plan",
        description=_clean(data.get("description"), 1000),
        exercises=exercises,
    )


async def generate_plan(
    db: Session,
    settings: nutrition_ai.AiSettings,
    prompt: str,
    language: str | None,
    model: str | None = None,
    user_id: int | None = None,
) -> workouts_schema.AiPlanDraft:
    """Full pipeline: catalog excerpt → LLM → validated ``AiPlanDraft``.

    When the user has a training inventory (``user_equipment``), the catalog
    is filtered to what they own and the inventory block is appended to the
    request so the model can pick feasible exercises and real weights.
    """
    inventory_text, allowed_equipment = inventory_block(db, user_id)
    try:
        excerpt = build_catalog_excerpt(db, prompt, language, allowed_equipment)
        if not excerpt and allowed_equipment is not None:
            # Inventory filter starved the (keyword-narrowed) excerpt — retry
            # against the full catalog rather than failing the request.
            excerpt = build_catalog_excerpt(db, "", language, allowed_equipment)
    except FileNotFoundError as e:
        # Snapshot missing (image built without backend/assets) would
        # surface as a raw HTTP 500 — turn it into an actionable message.
        raise AiPlanError(
            "Exercise catalog is not bundled with this server — update the server image and restart the container"
        ) from e
    if not excerpt:
        raise AiPlanError("Exercise catalog is empty — restart the server to re-seed it")
    catalog_text = "\n".join(excerpt)
    user_message = (
        f"User request: {prompt.strip()}\n\n"
        f"Catalog (id | name | category | equipment), {len(excerpt)} entries:\n"
        f"{catalog_text}"
    )
    if inventory_text:
        user_message = f"{inventory_text}\n\n{user_message}"
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT_TEMPLATE.replace("<lang>", language or "en")},
        {"role": "user", "content": user_message},
    ]
    if not (settings.base_url and settings.api_key and settings.model):
        # Defensive: the router checks `configured` before calling, but a
        # partially-filled settings row must not reach httpx as None.
        raise AiPlanError("AI provider settings are incomplete")
    reply = await nutrition_ai.chat_completion(
        settings.base_url, settings.api_key, settings.model, messages, timeout=HTTP_TIMEOUT
    )
    try:
        draft = validate_draft(parse_plan_json(reply), db, language)
    except AiPlanError as e:
        core_logger.print_to_log(f"AI plan generation: {e}", "error", exc=e)
        raise
    draft.model = model or settings.model
    return draft
