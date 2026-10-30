"""Post-process the exercise catalog snapshot: extra source + Russian names.

Two enrichments are applied on top of the wger-derived snapshot
(``scripts/generate_exercise_catalog.py``):

1. **Extra exercises** from the public-domain wrkout dataset
   (https://github.com/wrkout/exercises.json, Unlicense) — a directory of
   ``<Exercise>/exercise.json`` files with English names, instructions and
   muscle/equipment tags. Fields are mapped into the wger snapshot wire
   format (category/equipment/muscle dictionaries); synthetic ids are
   allocated in the 10000+ range, derived deterministically from the
   exercise name so re-runs and later additions never renumber rows
   (plans reference ``wger_exercise_id``).

2. **Russian display names** from ``assets/exercise_names_ru.json``
   (``{"<exercise id>": "Жим лёжа"}``). The translation is appended to the
   ``translations`` list as ``{"language": "ru", ...}``; an existing
   wger-provided Russian translation is never overwritten.

3. **Russian descriptions + technique tips** from
   ``assets/exercise_descriptions_ru.json``
   (``{"<exercise id>": {"description": "...", "tip": "..."}}``).
   Fills the ``ru`` translation's ``description`` (only when empty — native
   wger Russian text wins) and sets ``tips["ru"] = [tip]`` when the snapshot
   has no Russian tips yet. This is the landing zone for the batch pipeline:
   call ``POST /workouts/exercises/{wger_id}/translate`` per missing id and
   store the results in that file, then re-run this script.

Usage (after ``generate_exercise_catalog.py`` or standalone):

    python scripts/enrich_catalog.py [extra_dir] [ru_names_file] [snapshot]

All arguments are optional — defaults point at the in-repo snapshot and the
``exercises.json-master/`` checkout in the repository root (if present).
The descriptions overlay is always read from
``assets/exercise_descriptions_ru.json`` when present (no CLI arg yet —
the file is the batch pipeline's output).
Running it twice is a no-op for exercises already merged.
"""

import json
import sys
import zlib
from datetime import date
from pathlib import Path

_BACKEND_DIR = Path(__file__).resolve().parent.parent
_REPO_ROOT = _BACKEND_DIR.parent
DEFAULT_SNAPSHOT = _BACKEND_DIR / "assets" / "exercise_catalog.json"
DEFAULT_RU_NAMES = _BACKEND_DIR / "assets" / "exercise_names_ru.json"
DEFAULT_RU_DESCRIPTIONS = _BACKEND_DIR / "assets" / "exercise_descriptions_ru.json"
DEFAULT_EXTRA_DIR = _REPO_ROOT / "exercises.json-master" / "exercises"

# Synthetic id range for extra (non-wger) exercises: 10000..99999.
_EXTRA_ID_BASE = 10000
_EXTRA_ID_SPACE = 90000

# wrkout ``category`` field holds an activity type, not a body part — the
# snapshot categories are wger body-part groups, so the category is derived
# from the primary muscles instead (fallbacks below).
_PRIMARY_MUSCLE_TO_CATEGORY = {
    "shoulders": 13,  # Shoulders
    "lats": 12,  # Back
    "middle back": 12,
    "lower back": 12,
    "traps": 12,
    "biceps": 8,  # Arms
    "triceps": 8,
    "forearms": 8,
    "abdominals": 10,  # Abs
    "chest": 11,  # Chest
    "hamstrings": 9,  # Legs
    "quadriceps": 9,
    "glutes": 9,
    "adductors": 9,
    "calves": 14,  # Calves
}
_ACTIVITY_TYPE_TO_CATEGORY = {"cardio": 15, "plyometrics": 9, "stretching": 9}
_DEFAULT_CATEGORY = 9  # Legs — least wrong fallback for unmapped full-body work

# wrkout muscle tags -> snapshot muscle ids (dictionary extended with
# Adductors/Abductors/Forearms below — wger's fixture has no such entries).
_PRIMARY_MUSCLE_TO_ID = {
    "shoulders": 2,
    "lats": 12,
    "middle back": 9,
    "lower back": 16,
    "traps": 9,
    "biceps": 1,
    "triceps": 5,
    "forearms": 19,
    "abdominals": 6,
    "chest": 4,
    "hamstrings": 11,
    "quadriceps": 10,
    "glutes": 8,
    "adductors": 17,
    "calves": 7,
    "abductors": 18,
}

# wrkout equipment strings -> snapshot equipment ids. Rows without equipment
# (bodyweight stretching) map to the existing "none (bodyweight exercise)".
_EQUIPMENT_TO_ID = {
    "barbell": [1],
    "ez bar": [2],
    "dumbbell": [3],
    "exercise ball": [5],
    "body only": [7],
    "kettlebells": [10],
    "bands": [11],
    "cable": [12],
    "machine": [13],
    "medicine ball": [14],
    "foam roll": [15],
    "other": [16],
    "": [7],
    None: [7],
}

# Dictionary rows appended to the snapshot (ids continue past wger's 1-12/1-16).
_EXTRA_EQUIPMENT = [
    {"id": 13, "name": "Machine"},
    {"id": 14, "name": "Medicine ball"},
    {"id": 15, "name": "Foam roller"},
    {"id": 16, "name": "Other"},
]
_EXTRA_MUSCLES = [
    {"id": 17, "name": "Adductor group", "name_en": "Adductors", "is_front": True},
    {"id": 18, "name": "Hip abductors", "name_en": "Abductors", "is_front": True},
    {"id": 19, "name": "Forearm flexors", "name_en": "Forearms", "is_front": True},
]


def _stable_extra_id(name: str, taken: set[int]) -> int:
    """Deterministic id in 10000+ derived from the name; probes on collision."""
    candidate = _EXTRA_ID_BASE + zlib.crc32(name.encode("utf-8")) % _EXTRA_ID_SPACE
    while candidate in taken:
        candidate += 1 if candidate < _EXTRA_ID_BASE + _EXTRA_ID_SPACE - 1 else -(_EXTRA_ID_SPACE - 1)
    return candidate


def _category_for(fields: dict) -> int:
    primaries = [m.lower() for m in (fields.get("primaryMuscles") or [])]
    for muscle in primaries:
        if muscle in _PRIMARY_MUSCLE_TO_CATEGORY:
            return _PRIMARY_MUSCLE_TO_CATEGORY[muscle]
    activity = (fields.get("category") or "").lower()
    return _ACTIVITY_TYPE_TO_CATEGORY.get(activity, _DEFAULT_CATEGORY)


def _extra_exercise(fields: dict, taken: set[int]) -> dict:
    name = fields["name"]
    instructions = fields.get("instructions") or []
    translations = [
        {
            "language": "en",
            "name": name,
            "description": "\n".join(instructions),
        }
    ]
    muscles = [m for m in (_PRIMARY_MUSCLE_TO_ID.get(x.lower()) for x in (fields.get("primaryMuscles") or [])) if m]
    muscles_secondary = [
        m for m in (_PRIMARY_MUSCLE_TO_ID.get(x.lower()) for x in (fields.get("secondaryMuscles") or [])) if m
    ]
    return {
        "id": _stable_extra_id(name, taken),
        "uuid": f"wrkout-{zlib.crc32(name.encode('utf-8')):08x}",
        "category": _category_for(fields),
        "equipment": _EQUIPMENT_TO_ID.get((fields.get("equipment") or "").lower(), [7]),
        "muscles": muscles,
        "muscles_secondary": muscles_secondary,
        "variation_group": None,
        "license_author": "wrkout/exercises.json",
        "license": "Unlicense (public domain)",
        "translations": translations,
        "aliases": {},
        "tips": {},
    }


def merge_extra(snapshot: dict, extra_dir: Path) -> int:
    """Append wrkout exercises missing from the snapshot. Returns rows added."""
    if not extra_dir.is_dir():
        return 0
    by_id = {e["id"] for e in snapshot["exercises"]}
    added = 0
    # Sorted for a stable first-time allocation order.
    for entry in sorted(extra_dir.iterdir()):
        source = entry / "exercise.json"
        if not source.is_file():
            continue
        fields = json.loads(source.read_text(encoding="utf-8"))
        if not fields.get("name"):
            continue
        exercise = _extra_exercise(fields, set(by_id))
        if exercise["id"] in by_id:
            continue  # already merged (id is name-stable)
        snapshot["exercises"].append(exercise)
        by_id.add(exercise["id"])
        added += 1
    if added:
        snapshot["exercises"].sort(key=lambda e: e["id"])
        snapshot["count"] = len(snapshot["exercises"])
        snapshot["imported"] = date.today().isoformat()
    # Extend dictionaries (idempotent — skip ids already present).
    equip_ids = {e["id"] for e in snapshot["equipment"]}
    snapshot["equipment"].extend(row for row in _EXTRA_EQUIPMENT if row["id"] not in equip_ids)
    muscle_ids = {m["id"] for m in snapshot["muscles"]}
    snapshot["muscles"].extend(row for row in _EXTRA_MUSCLES if row["id"] not in muscle_ids)
    return added


def apply_russian_names(snapshot: dict, ru_names: dict[str, str]) -> int:
    """Append ``ru`` translations missing from the snapshot. Returns rows touched."""
    touched = 0
    for exercise in snapshot["exercises"]:
        wanted = ru_names.get(str(exercise["id"]))
        if not wanted:
            continue
        if any(tr.get("language") == "ru" and tr.get("name") for tr in exercise["translations"]):
            continue  # keep the native wger Russian translation when present
        exercise["translations"].append({"language": "ru", "name": wanted, "description": ""})
        # English stays first for the deterministic seed/display fallback.
        exercise["translations"].sort(key=lambda t: (t["language"] != "en", t["language"]))
        touched += 1
    return touched


def apply_russian_descriptions(snapshot: dict, ru_texts: dict[str, dict]) -> int:
    """Fill ``ru`` descriptions + tips from the batch overlay. Returns rows touched."""
    touched = 0
    for exercise in snapshot["exercises"]:
        wanted = ru_texts.get(str(exercise["id"]))
        if not isinstance(wanted, dict):
            continue
        ru_tr = next((tr for tr in exercise["translations"] if tr.get("language") == "ru"), None)
        if ru_tr is None:
            continue  # names overlay runs first; without a ru name row skip descriptions
        changed = False
        description = str(wanted.get("description") or "").strip()
        if description and not str(ru_tr.get("description") or "").strip():
            ru_tr["description"] = description
            changed = True
        tip = str(wanted.get("tip") or "").strip()
        tips = exercise.setdefault("tips", {})
        if tip and not tips.get("ru"):
            tips["ru"] = [tip]
            changed = True
        touched += int(changed)
    return touched


def write_snapshot(snapshot: dict, path: Path) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(snapshot, fh, ensure_ascii=False, separators=(",", ":"))


def main() -> int:
    extra_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_EXTRA_DIR
    ru_file = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_RU_NAMES
    snapshot_path = Path(sys.argv[3]) if len(sys.argv) > 3 else DEFAULT_SNAPSHOT

    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    added = merge_extra(snapshot, extra_dir)
    ru_names: dict[str, str] = {}
    if ru_file.is_file():
        ru_names = json.loads(ru_file.read_text(encoding="utf-8"))
    translated = apply_russian_names(snapshot, ru_names)
    ru_texts: dict[str, dict] = {}
    if DEFAULT_RU_DESCRIPTIONS.is_file():
        ru_texts = json.loads(DEFAULT_RU_DESCRIPTIONS.read_text(encoding="utf-8"))
    described = apply_russian_descriptions(snapshot, ru_texts)
    write_snapshot(snapshot, snapshot_path)

    untranslated = [e["id"] for e in snapshot["exercises"] if not any(t["language"] == "ru" for t in e["translations"])]
    undescribed = [
        e["id"]
        for e in snapshot["exercises"]
        if not next((t for t in e["translations"] if t["language"] == "ru"), {}).get("description")
    ]
    print(
        f"Enriched {snapshot_path}: +{added} extra exercises, +{translated} ru names, "
        f"+{described} ru descriptions, total {snapshot['count']}; "
        f"without ru: {len(untranslated)}, without ru description: {len(undescribed)}"
        + (f" ids={undescribed[:20]}" if undescribed else "")
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
