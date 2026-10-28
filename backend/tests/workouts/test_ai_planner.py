"""Tests for the AI plan generator's reply parsing and validation."""

from unittest.mock import MagicMock, patch

import pytest

import workouts.ai_planner as workouts_ai_planner
import workouts.exercise_catalog as exercise_catalog


def _catalog_row(wger_id: int, en: str, ru: str | None = None) -> MagicMock:
    row = MagicMock(spec=exercise_catalog.ExerciseCatalog)
    row.wger_id = wger_id
    row.name = en
    translations: dict = {"en": {"name": en, "description": ""}}
    if ru:
        translations["ru"] = {"name": ru, "description": ""}
    row.translations = translations
    return row


GOOD_JSON = """{
  "name": "Грудь + трицепс",
  "description": "Базовая тренировка груди",
  "exercises": [
    {"wger_exercise_id": 9, "name": "Bench Press", "muscle_group": "Chest",
     "day_label": "День 1", "target_sets": 4, "target_reps": "8-12",
     "target_weight_kg": null, "rest_s": 90, "notes": "Техника прежде веса"},
    {"wger_exercise_id": 777, "name": "Ghost Exercise", "muscle_group": "Chest",
     "day_label": "День 1", "target_sets": 3, "target_reps": "10"}
  ]
}"""


class TestParsePlanJson:
    def test_plain_json(self) -> None:
        data = workouts_ai_planner.parse_plan_json(GOOD_JSON)
        assert data["name"] == "Грудь + трицепс"
        assert len(data["exercises"]) == 2

    def test_markdown_fenced(self) -> None:
        fenced = "```json\n" + GOOD_JSON + "\n```"
        data = workouts_ai_planner.parse_plan_json(fenced)
        assert data["name"] == "Грудь + трицепс"

    def test_prose_around_json(self) -> None:
        wrapped = "Вот твой план:\n" + GOOD_JSON + "\nПриятных тренировок!"
        data = workouts_ai_planner.parse_plan_json(wrapped)
        assert len(data["exercises"]) == 2

    def test_no_json_raises(self) -> None:
        with pytest.raises(workouts_ai_planner.AiPlanError):
            workouts_ai_planner.parse_plan_json("no json here at all")

    def test_broken_json_raises(self) -> None:
        with pytest.raises(workouts_ai_planner.AiPlanError):
            workouts_ai_planner.parse_plan_json('{"name": "x", "exercises": [')

    def test_missing_exercises_raises(self) -> None:
        with pytest.raises(workouts_ai_planner.AiPlanError):
            workouts_ai_planner.parse_plan_json('{"name": "x"}')


class TestValidateDraft:
    def test_hallucinated_id_dropped_and_localized_name(self, mock_db) -> None:
        # id 9 resolves to a catalog row, any other id is unknown to the db.
        mock_db.get.side_effect = lambda _model, pk: _catalog_row(9, "Bench Press", "Жим лёжа") if pk == 9 else None
        draft = workouts_ai_planner.validate_draft(workouts_ai_planner.parse_plan_json(GOOD_JSON), mock_db, "ru")
        assert len(draft.exercises) == 1
        assert draft.exercises[0].wger_exercise_id == 9
        assert draft.exercises[0].name == "Жим лёжа"
        assert draft.name == "Грудь + трицепс"
        assert draft.exercises[0].target_sets == 4
        assert draft.exercises[0].rest_s == 90

    def test_unknown_id_without_row_keeps_ai_name(self, mock_db) -> None:
        mock_db.get.return_value = None
        payload = '{"exercises": [{"wger_exercise_id": null, "name": "Free weight row", "target_sets": 3}]}'
        draft = workouts_ai_planner.validate_draft(workouts_ai_planner.parse_plan_json(payload), mock_db, "en")
        assert draft.exercises[0].name == "Free weight row"
        assert draft.exercises[0].wger_exercise_id is None

    def test_max_exercises_cap(self, mock_db) -> None:
        mock_db.get.return_value = None
        rows = ",".join(f'{{"wger_exercise_id": null, "name": "Ex {i}"}}' for i in range(50))
        payload = '{"exercises": [' + rows + "]}"

        draft = workouts_ai_planner.validate_draft(workouts_ai_planner.parse_plan_json(payload), mock_db, "en")

        assert len(draft.exercises) == workouts_ai_planner.MAX_EXERCISES

    def test_no_usable_exercises_raises(self, mock_db) -> None:
        mock_db.get.return_value = None
        payload = '{"exercises": [{"wger_exercise_id": 42, "name": "Ghost"}]}'
        with pytest.raises(workouts_ai_planner.AiPlanError):
            workouts_ai_planner.validate_draft(workouts_ai_planner.parse_plan_json(payload), mock_db, "en")

    def test_string_numbers_sanitised(self, mock_db) -> None:
        mock_db.get.return_value = None
        payload = '{"exercises": [{"name": "X", "target_sets": "3", "target_reps": 12, "rest_s": "90", "target_weight_kg": "60"}]}'
        draft = workouts_ai_planner.validate_draft(workouts_ai_planner.parse_plan_json(payload), mock_db, "en")
        row = draft.exercises[0]
        assert row.target_sets == 3
        assert row.target_reps == "12"
        assert row.rest_s == 90
        assert row.target_weight_kg == 60.0


class TestCatalogExcerpt:
    def test_lines_format(self) -> None:
        row = _catalog_row(9, "Bench Press", "Жим лёжа")
        row.category_id = 2
        row.equipment_ids = [1, 3]
        db = MagicMock()

        with patch.object(exercise_catalog, "load_snapshot") as snap:
            snap.return_value = {
                "categories": [{"id": 2, "name": "Chest"}],
                "equipment": [{"id": 1, "name": "Barbell"}, {"id": 3, "name": "Bench"}],
            }
            with patch.object(workouts_ai_planner, "_catalog_rows", return_value=[row]):
                lines = workouts_ai_planner.build_catalog_excerpt(db, "накачать грудь", "ru")
        assert lines == ["9 | Жим лёжа | Chest | Barbell, Bench"]

    def test_focus_keywords(self) -> None:
        ids = workouts_ai_planner._focus_category_ids(
            "хочу накачать грудные мышцы",
            {1: "Arms", 2: "Chest", 3: "Back"},
        )
        assert ids == {2}


class TestGeneratePlanGuards:
    """The catalog guards must yield actionable AiPlanErrors, not HTTP 500s."""

    async def test_missing_snapshot_raises_actionable_error(self, mock_db) -> None:
        settings = MagicMock()
        with (
            patch.object(exercise_catalog, "load_snapshot", side_effect=FileNotFoundError),
            pytest.raises(workouts_ai_planner.AiPlanError, match="not bundled"),
        ):
            await workouts_ai_planner.generate_plan(mock_db, settings, "накачать бицепсы", "ru")

    async def test_empty_catalog_raises_actionable_error(self, mock_db) -> None:
        settings = MagicMock()
        with (
            patch.object(exercise_catalog, "load_snapshot", return_value={"categories": [], "equipment": []}),
            patch.object(workouts_ai_planner, "_catalog_rows", return_value=[]),
            pytest.raises(workouts_ai_planner.AiPlanError, match="empty"),
        ):
            await workouts_ai_planner.generate_plan(mock_db, settings, "накачать бицепсы", "ru")


class TestAiPlanDraftShape:
    def test_draft_fields_default_none(self, mock_db) -> None:
        """The draft rows must carry every field the plan editor needs."""
        mock_db.get.return_value = _catalog_row(9, "Bench Press")
        draft = workouts_ai_planner.validate_draft(
            workouts_ai_planner.parse_plan_json(
                '{"exercises": [{"wger_exercise_id": 9, "target_sets": 3, "target_reps": "8-12"}]}'
            ),
            mock_db,
            "en",
        )
        first = draft.exercises[0]
        assert first.name == "Bench Press"
        assert first.day_label is None
        assert first.notes is None
