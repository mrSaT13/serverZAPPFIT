"""Tests for the opt-in workout → activity feed publishing."""

from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock

import activities.activity.models as activities_models
import core.routes  # noqa: F401 — registers every model so ORM mappers initialise
import workouts.feed as workouts_feed


def _privacy(**overrides) -> MagicMock:
    row = MagicMock()
    row.publish_workouts_in_feed = overrides.get("publish", True)
    row.default_activity_visibility = overrides.get("visibility", "public")
    row.hide_activity_start_time = overrides.get("hide_start_time", False)
    row.hide_activity_location = False
    row.hide_activity_map = False
    row.hide_activity_hr = False
    row.hide_activity_power = False
    row.hide_activity_cadence = False
    row.hide_activity_elevation = False
    row.hide_activity_speed = False
    row.hide_activity_pace = False
    row.hide_activity_laps = False
    row.hide_activity_workout_sets_steps = False
    row.hide_activity_gear = False
    return row


def _session(**overrides) -> MagicMock:
    row = MagicMock()
    row.id = overrides.get("id", 55)
    row.user_id = 1
    row.plan_id = overrides.get("plan_id")
    row.date = overrides.get("date", date(2026, 10, 29))
    row.duration_min = overrides.get("duration_min", 45.0)
    row.calories = overrides.get("calories", 300.0)
    row.comment = overrides.get("comment")
    row.activity_id = overrides.get("activity_id")
    row.sets = overrides.get("sets", [])
    return row


def _db(privacy, user=None) -> MagicMock:
    db = MagicMock()
    db.execute.return_value.scalar_one_or_none.return_value = privacy
    db.get.return_value = user
    return db


class TestPublishSessionActivity:
    def test_skipped_when_privacy_row_missing(self) -> None:
        db = _db(privacy=None)
        workouts_feed.publish_session_activity(1, _session(), db)
        db.add.assert_not_called()

    def test_skipped_when_setting_disabled(self) -> None:
        db = _db(_privacy(publish=False))
        workouts_feed.publish_session_activity(1, _session(), db)
        db.add.assert_not_called()

    def test_skipped_when_already_published(self) -> None:
        db = _db(_privacy())
        workouts_feed.publish_session_activity(1, _session(activity_id=99), db)
        db.add.assert_not_called()

    def test_creates_strength_activity_with_session_metrics(self) -> None:
        db = _db(_privacy(), user=SimpleNamespace(preferred_language="en"))
        session = _session(duration_min=45.0, calories=300.0)

        workouts_feed.publish_session_activity(1, session, db)

        db.add.assert_called_once()
        activity = db.add.call_args.args[0]
        assert isinstance(activity, activities_models.Activity)
        assert activity.activity_type == workouts_feed.ACTIVITY_TYPE_STRENGTH == 19
        assert activity.distance == 0
        assert activity.calories == 300
        assert float(activity.total_elapsed_time) == 45.0 * 60
        # Anchored at noon UTC on the session date.
        assert activity.start_time.date() == session.date
        # The link flush happens inside the same transaction.
        db.flush.assert_called_once()
        db.commit.assert_called_once()

    def test_name_prefers_plan_then_comment_then_default(self) -> None:
        db = _db(_privacy(), user=SimpleNamespace(preferred_language="en"))
        session = _session(comment="Leg day")
        workouts_feed.publish_session_activity(1, session, db)
        assert db.add.call_args.args[0].name == "Leg day"

        db2 = _db(_privacy(), user=SimpleNamespace(preferred_language="ru"))
        session2 = _session(comment=None)
        workouts_feed.publish_session_activity(1, session2, db2)
        assert db2.add.call_args.args[0].name == "Силовая тренировка"

    def test_ru_summary_in_description(self) -> None:
        completed = [
            MagicMock(completed=True, exercise_name="Жим", weight_kg=60.0, reps=8),
            MagicMock(completed=True, exercise_name="Тяга", weight_kg=50.0, reps=10),
            MagicMock(completed=False, exercise_name="Присед", weight_kg=0, reps=0),
        ]
        db = _db(_privacy(), user=SimpleNamespace(preferred_language="ru-RU"))
        session = _session(comment=None, sets=completed)

        workouts_feed.publish_session_activity(1, session, db)

        description = db.add.call_args.args[0].description
        # Only completed sets count: 2 exercises, 2 sets, 60*8 + 50*10 = 980 kg.
        assert "2 упражнений" in description
        assert "2 подходов" in description
        assert "980 кг" in description

    def test_visibility_maps_default_setting(self) -> None:
        db = _db(_privacy(visibility="followers"), user=SimpleNamespace(preferred_language="en"))
        workouts_feed.publish_session_activity(1, _session(), db)
        assert db.add.call_args.args[0].visibility == 1

        db2 = _db(_privacy(visibility="private"), user=SimpleNamespace(preferred_language="en"))
        workouts_feed.publish_session_activity(1, _session(), db2)
        assert db2.add.call_args.args[0].visibility == 2

    def test_hide_flags_mirror_privacy_settings(self) -> None:
        db = _db(_privacy(hide_start_time=True), user=SimpleNamespace(preferred_language="en"))
        workouts_feed.publish_session_activity(1, _session(), db)
        activity = db.add.call_args.args[0]
        assert activity.hide_start_time is True
        assert activity.hide_map is False
        assert activity.is_hidden is False


class TestDeletePublishedActivity:
    def test_deletes_by_id(self) -> None:
        db = MagicMock()
        workouts_feed.delete_published_activity(7, db)
        db.execute.assert_called_once()
        db.commit.assert_called_once()

    def test_failure_is_swallowed(self) -> None:
        db = MagicMock()
        db.execute.side_effect = RuntimeError("db down")
        # Must not raise — feed cleanup can never block a session delete.
        workouts_feed.delete_published_activity(7, db)
        db.rollback.assert_called_once()
