"""wger routine import (wger 2.x "routine" API: routine -> structure).

Hierarchy mapped onto ZAPFIT:
    Routine  -> WorkoutPlan
    Day      -> day_label group (rest days are skipped)
    Slot     -> ordering only (slot order folds into exercise position)
    SlotEntry-> WorkoutExercise (name, sets/reps/weight/rest from iteration-1
                configs; progressive rule configs are simplified to their
                starting values — re-import refreshes them)

All requests run through a single pooled httpx.Client per import/preview call.
"""

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

import core.cryptography as core_cryptography
import core.logger as core_logger
import nutrition.models as nutrition_models
import workouts.exercise_catalog as exercise_catalog
import workouts.schema as workouts_schema

REQUEST_TIMEOUT = 20.0


class WgerImportError(Exception):
    """Raised when the remote wger instance is unreachable or errors out."""


class WgerClient:
    """Thin pooled client over a user's stored wger (nutrition) settings."""

    def __init__(self, token_user_id: int, db: Session) -> None:
        self._session = db
        stmt = select(nutrition_models.UserNutritionSettings).where(
            nutrition_models.UserNutritionSettings.user_id == token_user_id
        )
        row = db.scalars(stmt).first()
        base_url = (row.wger_base_url or "").rstrip("/") if row else ""
        enabled = bool(row.wger_enabled) if row else False
        token = core_cryptography.decrypt_token_fernet(row.wger_api_key) if row and row.wger_api_key else None
        if not base_url or not enabled or not token:
            raise WgerImportError("wger integration is not configured — set URL and API key in Integrations first")
        self._client = httpx.Client(
            base_url=f"{base_url}/api/v2",
            headers={"Authorization": f"Token {token}"},
            timeout=REQUEST_TIMEOUT,
        )

    def __enter__(self) -> "WgerClient":
        return self

    def __exit__(self, *exc: object) -> None:
        self._client.close()

    def get(self, path: str, params: dict | None = None) -> dict | list:
        try:
            r = self._client.get(path, params=params)
            r.raise_for_status()
            return r.json()
        except httpx.HTTPError as e:
            core_logger.print_to_log(f"wger import request failed: {e}", "error", exc=e)
            raise WgerImportError(f"wger request failed: {path}") from e

    def page(self, path: str, params: dict | None = None) -> list[dict]:
        """Unwrap wger DRF pagination ({count, next, results}) or bare lists."""
        data = self.get(path, params)
        if isinstance(data, list):
            return data
        return data.get("results", []) if isinstance(data, dict) else []

    def exercise_names(self, needed_ids: set[int], lang_priority: tuple[str, ...] = ("en",)) -> dict[int, str]:
        """Map wger exercise id -> display name.

        Resolves from the local (seeded) exercise catalog first; unknown ids
        fall back to a per-id remote lookup so freshly added wger exercises
        still import.
        """
        out: dict[int, str] = {}
        missing: set[int] = set()
        rows = self._session.scalars(
            select(exercise_catalog.ExerciseCatalog).where(exercise_catalog.ExerciseCatalog.wger_id.in_(needed_ids))
        ).all()
        for row in rows:
            names = {lang: tr.get("name") for lang, tr in (row.translations or {}).items()}
            name = None
            for lang in lang_priority:
                name = names.get(lang)
                if name:
                    break
            out[row.wger_id] = name or next(iter(names.values()), "")
            missing.discard(row.wger_id)
        missing = needed_ids - set(out)
        for ex_id in missing:
            info = self.get(f"/exerciseinfo/{ex_id}/")
            if not isinstance(info, dict):
                continue
            names: dict[str, str] = {}
            for tr in info.get("translations") or []:
                if isinstance(tr, dict) and tr.get("name"):
                    names[(tr.get("language") or "").lower()] = tr["name"]
            name = None
            for lang in lang_priority:
                name = names.get(lang)
                if name:
                    break
            out[ex_id] = name or next(iter(names.values()), "")
        return out


def list_routines(token_user_id: int, db: Session) -> list[workouts_schema.WgerRoutinePreview]:
    """Brief preview of remote routines so the user can pick one to import."""
    with WgerClient(token_user_id, db) as wger:
        rows = wger.page("/routine/", params={"limit": 100})
        out: list[workouts_schema.WgerRoutinePreview] = []
        for r in rows:
            structure = wger.get(f"/routine/{r['id']}/structure/")
            days = structure.get("days") or [] if isinstance(structure, dict) else []
            out.append(
                workouts_schema.WgerRoutinePreview(
                    wger_id=r["id"],
                    name=r.get("name"),
                    start=r.get("start"),
                    end=r.get("end"),
                    days=len([d for d in days if not d.get("is_rest")]),
                    is_template=bool(r.get("is_template")),
                )
            )
        return out


def _config_value(configs: list[dict]) -> str | float | None:
    """Pick the iteration-1 (replace) value from a wger rule-config array."""
    for cfg in configs or []:
        if isinstance(cfg, dict) and cfg.get("iteration") == 1:
            return cfg.get("value")
    return None


def _as_int(value: str | float | None) -> int | None:
    return int(value) if isinstance(value, (int, float)) else None


def _as_float(value: str | float | None) -> float | None:
    return float(value) if isinstance(value, (int, float)) else None


def routine_to_plan(wger: WgerClient, wger_routine_id: int) -> workouts_schema.WorkoutPlanCreate:
    """Fetch one routine structure and map it to a ZAPFIT plan payload."""
    data = wger.get(f"/routine/{wger_routine_id}/structure/")
    if not isinstance(data, dict):
        raise WgerImportError("Unexpected wger structure response")

    needed_ids: set[int] = set()
    entries_by_day: list[tuple[str | None, list[dict]]] = []
    for day in sorted(data.get("days") or [], key=lambda d: d.get("order", 0)):
        if day.get("is_rest"):
            continue
        flat: list[tuple[float, dict]] = []
        for slot in day.get("slots") or []:
            for entry in slot.get("entries") or []:
                flat.append((float(slot.get("order", 0) or 0), entry))
        flat.sort(key=lambda t: t[0])
        entries_by_day.append((day.get("name") or None, [e for _, e in flat]))
        for _, entry in flat:
            if entry.get("exercise"):
                needed_ids.add(entry["exercise"])

    names = wger.exercise_names(needed_ids)

    exercises: list[workouts_schema.WorkoutExerciseIn] = []
    for day_label, entries in entries_by_day:
        for entry in entries:
            ex_id = entry.get("exercise")
            exercises.append(
                workouts_schema.WorkoutExerciseIn(
                    position=len(exercises),
                    day_label=day_label,
                    name=names.get(ex_id, f"wger exercise #{ex_id}"),
                    wger_exercise_id=ex_id,
                    notes=entry.get("comment") or None,
                    target_sets=_as_int(_config_value(entry.get("set_nr_configs") or [])),
                    target_reps=(
                        str(reps)
                        if (reps := _config_value(entry.get("repetitions_configs") or [])) is not None
                        else None
                    ),
                    target_weight_kg=_as_float(_config_value(entry.get("weight_configs") or [])),
                    rest_s=_as_int(_config_value(entry.get("rest_configs") or [])),
                )
            )
    if not exercises:
        raise WgerImportError("This wger routine has no exercises to import")

    return workouts_schema.WorkoutPlanCreate(
        name=data.get("name") or f"wger routine #{wger_routine_id}",
        description=data.get("description") or None,
        exercises=exercises,
    )


def import_routine(token_user_id: int, db: Session, wger_routine_id: int) -> workouts_schema.WorkoutPlanCreate:
    with WgerClient(token_user_id, db) as wger:
        return routine_to_plan(wger, wger_routine_id)
