"""Regenerate `backend/assets/exercise_catalog.json` from wger's Django fixtures.

The catalog snapshot bundled into ZAPFIT is a derived artifact of the wger
project (https://wger.de, AGPL; exercise data CC-BY-SA). This script is the
reproducible way to rebuild it when the wger source checkout is updated:

    python scripts/generate_exercise_catalog.py D:\\wger-master\\wger-master

Input (all under ``wger/wger/exercises/fixtures``):
- ``exercise-base-data.json``  — 872 exercise bases (ids, category, equipment,
  muscles, license)
- ``translations.json``        — mixed file: per-language names/descriptions
  PLUS exercise comments (tips) and aliases, both keyed by translation pk
- ``categories.json`` / ``equipment.json`` / ``muscles.json`` — dictionaries
- ``wger/core/fixtures/licenses.json`` — license id -> full name

Output: the snapshot consumed by ``workouts.exercise_catalog.seed_catalog``
(see the module docstring there for the wire format).
"""

import json
import sys
from datetime import date
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(_BACKEND_DIR / "app") not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR / "app"))

DEFAULT_OUT = _BACKEND_DIR / "assets" / "exercise_catalog.json"


def _load(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _dict_by_pk(items: list[dict], model: str) -> dict[int, dict]:
    return {item["pk"]: item["fields"] for item in items if item["model"] == model}


def _append_grouped(
    target: dict[int, dict[str, list[str]]], translation_pk: int, text: str, tr_exercise: dict[int, int]
) -> None:
    """Attach ``text`` to the exercise that owns the given translation."""
    exercise_pk = tr_exercise.get(translation_pk)
    lang = _translation_language.get(translation_pk)
    if exercise_pk is None or lang is None:
        return
    text = (text or "").strip()
    if not text:
        return
    bucket = target.setdefault(exercise_pk, {}).setdefault(lang, [])
    if text not in bucket:
        bucket.append(text)


def generate(wger_root: Path, out_path: Path) -> dict:
    fixtures = wger_root / "wger" / "exercises" / "fixtures"
    core_fixtures = wger_root / "wger" / "core" / "fixtures"

    base = _load(fixtures / "exercise-base-data.json")
    mixed = _load(fixtures / "translations.json")
    categories = _load(fixtures / "categories.json")
    equipment = _load(fixtures / "equipment.json")
    muscles = _load(fixtures / "muscles.json")
    licenses = _load(core_fixtures / "licenses.json")
    languages = _load(core_fixtures / "languages.json")

    # license id -> full CC name; attached to each exercise as a plain string.
    license_names = {lic["pk"]: (lic["fields"].get("full_name") or "").strip() or None for lic in licenses}

    # language pk -> short code ("de", "en", "ru", ...): fixture translations
    # reference languages by pk, but the snapshot wire format uses codes.
    lang_codes = {item["pk"]: (item["fields"].get("short_name") or str(item["pk"])) for item in languages}

    # translation pk -> language / exercise pk, built before the mixed file is
    # split (comments and aliases reference the translation pk, not the exercise).
    global _translation_language
    translations_by_pk: dict[int, dict] = {}
    _translation_language = {}
    for item in mixed:
        if item["model"] != "exercises.translation":
            continue
        fields = item["fields"]
        translations_by_pk[item["pk"]] = fields
        _translation_language[item["pk"]] = lang_codes.get(fields["language"], str(fields["language"]))
    tr_exercise = {pk: f["exercise"] for pk, f in translations_by_pk.items()}

    tips: dict[int, dict[str, list[str]]] = {}
    aliases: dict[int, dict[str, list[str]]] = {}
    for item in mixed:
        if item["model"] == "exercises.exercisecomment":
            _append_grouped(tips, item["fields"]["translation"], item["fields"].get("comment", ""), tr_exercise)
        elif item["model"] == "exercises.alias":
            _append_grouped(aliases, item["fields"]["translation"], item["fields"].get("alias", ""), tr_exercise)

    exercises = []
    for item in base:
        pk = item["pk"]
        fields = item["fields"]
        exercise_translations = [
            {
                "language": lang_codes.get(f["language"], str(f["language"])),
                "name": f["name"],
                "description": f.get("description") or "",
            }
            for f in translations_by_pk.values()
            if f["exercise"] == pk
        ]
        # English first (always present), then alphabetical — stable output.
        exercise_translations.sort(key=lambda t: (t["language"] != "en", t["language"]))
        license_name = license_names.get(fields.get("license"))
        exercises.append(
            {
                "id": pk,
                "uuid": fields["uuid"],
                "category": fields["category"],
                "equipment": fields.get("equipment") or [],
                "muscles": fields.get("muscles") or [],
                "muscles_secondary": fields.get("muscles_secondary") or [],
                "variation_group": fields.get("variation_group"),
                "license_author": fields.get("license_author") or "",
                "license": license_name,
                "translations": exercise_translations,
                "aliases": aliases.get(pk, {}),
                "tips": tips.get(pk, {}),
            }
        )
    exercises.sort(key=lambda e: e["id"])

    snapshot = {
        "source": "wger (https://wger.de) — AGPL project, exercise data CC-BY-SA",
        "licenses": {str(pk): name for pk, name in sorted(license_names.items())},
        "imported": date.today().isoformat(),
        "count": len(exercises),
        "categories": [
            {"id": pk, "name": f["name"]}
            for pk, f in sorted(_dict_by_pk(categories, "exercises.exercisecategory").items())
        ],
        "equipment": [
            {"id": pk, "name": f["name"]} for pk, f in sorted(_dict_by_pk(equipment, "exercises.equipment").items())
        ],
        "muscles": [
            {
                "id": pk,
                "name": f["name"],
                "name_en": f.get("name_en") or "",
                "is_front": bool(f.get("is_front")),
            }
            for pk, f in sorted(_dict_by_pk(muscles, "exercises.muscle").items())
        ],
        "exercises": exercises,
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8", newline="\n") as fh:
        # Single-line compact JSON, matching the original snapshot format so
        # diffs stay reviewable (one logical line per exercise group).
        json.dump(snapshot, fh, ensure_ascii=False, separators=(",", ":"))
    return snapshot


# Populated in generate() before _append_grouped is used; module-level so the
# helper stays a plain function (keeps the mixed-file pass simple).
_translation_language: dict[int, str] = {}


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    wger_root = Path(sys.argv[1])
    out_path = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_OUT
    snapshot = generate(wger_root, out_path)
    with_tips = sum(1 for e in snapshot["exercises"] if e["tips"])
    with_aliases = sum(1 for e in snapshot["exercises"] if e["aliases"])
    print(
        f"Wrote {out_path}: {snapshot['count']} exercises, "
        f"{with_tips} with tips, {with_aliases} with aliases, "
        f"{len(snapshot['licenses'])} licenses"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
