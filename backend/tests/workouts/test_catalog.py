"""Tests for catalog search enrichment (aliases, tips, license names)."""

from unittest.mock import MagicMock

import workouts.catalog_router as catalog_router
import workouts.exercise_catalog as exercise_catalog


def _row(**overrides) -> MagicMock:
    row = MagicMock(spec=exercise_catalog.ExerciseCatalog)
    row.wger_id = 9
    row.uuid = "u-9"
    row.name = "Bench Press"
    row.translations = {"en": {"name": "Bench Press", "description": ""}}
    row.category_id = 11
    row.muscle_ids = []
    row.muscle_ids_secondary = []
    row.equipment_ids = []
    row.variation_group = None
    row.license_author = "tester"
    row.aliases = {}
    row.tips = {}
    row.license_name = None
    for key, value in overrides.items():
        setattr(row, key, value)
    return row


class TestMatchesQuery:
    def test_matches_canonical_name(self) -> None:
        assert catalog_router._matches_query(_row(), "bench")

    def test_matches_translation_name(self) -> None:
        row = _row(translations={"ru": {"name": "Жим лёжа", "description": ""}})
        assert catalog_router._matches_query(row, "жим")

    def test_matches_alias(self) -> None:
        row = _row(aliases={"ru": ["Становая тяга"], "en": ["Deadlift"]})
        assert catalog_router._matches_query(row, "станов")
        assert catalog_router._matches_query(row, "deadlift")

    def test_no_match(self) -> None:
        assert not catalog_router._matches_query(_row(), "йога")


class TestToRead:
    def test_exposes_enrichment_fields(self) -> None:
        snapshot = {
            "categories": [{"id": 11, "name": "Chest"}],
            "equipment": [],
            "muscles": [],
        }
        row = _row(
            aliases={"en": ["Flat press"]},
            tips={"en": ["Keep your back flat"]},
            license_name="Creative Commons Attribution Share Alike 4",
        )

        read = catalog_router._to_read(row, snapshot)

        assert read.aliases == {"en": ["Flat press"]}
        assert read.tips == {"en": ["Keep your back flat"]}
        assert read.license == "Creative Commons Attribution Share Alike 4"
        assert read.category == {"id": 11, "name": "Chest"}

    def test_missing_enrichment_defaults_to_empty(self) -> None:
        snapshot = {"categories": [], "equipment": [], "muscles": []}
        row = _row(aliases=None, tips=None, license_name=None)

        read = catalog_router._to_read(row, snapshot)

        assert read.aliases == {}
        assert read.tips == {}
        assert read.license is None
