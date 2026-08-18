"""Tests for FIT activity file import utilities."""

from datetime import UTC, datetime
from types import SimpleNamespace

import activities.activity_file_import.utils_fit as utils_fit


def _privacy_settings() -> SimpleNamespace:
    """
    Build privacy settings for parser tests.

    Returns:
        Object with the attributes expected by privacy kwarg builder.
    """
    return SimpleNamespace(
        default_activity_visibility="public",
        hide_activity_start_time=False,
        hide_activity_location=False,
        hide_activity_map=False,
        hide_activity_hr=False,
        hide_activity_power=False,
        hide_activity_cadence=False,
        hide_activity_elevation=False,
        hide_activity_speed=False,
        hide_activity_pace=False,
        hide_activity_laps=False,
        hide_activity_workout_sets_steps=False,
        hide_activity_gear=False,
    )


def _session_record(manufacturer, product=None) -> dict:
    """
    Build a minimal FIT session record for create_activity_objects.

    Args:
        manufacturer: Value placed in file_id["manufacturer"].
        product: Value placed in file_id["product"].

    Returns:
        Session record dict with the keys the builder reads.
    """
    start = datetime(2026, 6, 20, 8, 20, 3, tzinfo=UTC)
    end = datetime(2026, 6, 20, 9, 43, 29, tzinfo=UTC)
    return {
        "activity_name": "Workout",
        "time_offset": None,
        "is_lat_lon_set": False,
        "is_power_set": False,
        "lat_lon_waypoints": [],
        "ele_waypoints": [],
        "power_waypoints": [],
        "hr_waypoints": [],
        "vel_waypoints": [],
        "pace_waypoints": [],
        "cad_waypoints": [],
        "temp_waypoints": [],
        "laps": [],
        "sets": [],
        "workout_steps": [],
        "split_summary": [],
        "lengths": [],
        "file_id": {"manufacturer": manufacturer, "product": product},
        "session": {
            "activity_type": None,
            "first_waypoint_time": start,
            "last_waypoint_time": end,
            "distance": None,
            "total_elapsed_time": 5006.0,
            "total_timer_time": 5006.0,
            "city": None,
            "town": None,
            "country": None,
            "ele_gain": None,
            "ele_loss": None,
            "avg_speed": None,
            "max_speed": None,
            "avg_power": None,
            "max_power": None,
            "np": None,
            "avg_hr": 145,
            "max_hr": 177,
            "avg_cadence": None,
            "max_cadence": None,
            "workout_feeling": None,
            "workout_rpe": None,
            "calories": 934,
            "total_cycles": None,
        },
    }


class TestUtilsFit:
    """Test suite for FIT parser helper functions."""

    def test_create_activity_objects_stringifies_numeric_manufacturer(self):
        """Numeric FIT manufacturer ids are coerced to strings."""
        # Some devices (e.g. Amazfit/Zepp) report an unmapped numeric
        # manufacturer id rather than a name; the schema expects a string.
        activities = utils_fit.create_activity_objects(
            [_session_record(339)],
            user_id=1,
            user_privacy_settings=_privacy_settings(),
        )

        assert len(activities) == 1
        assert activities[0]["activity"].tracker_manufacturer == "339"

    def test_create_activity_objects_keeps_none_manufacturer(self):
        """A missing manufacturer stays None instead of the string 'None'."""
        activities = utils_fit.create_activity_objects(
            [_session_record(None)],
            user_id=1,
            user_privacy_settings=_privacy_settings(),
        )

        assert activities[0]["activity"].tracker_manufacturer is None

    def test_create_activity_objects_stringifies_numeric_model(self):
        """Numeric FIT product ids are coerced to strings."""
        activities = utils_fit.create_activity_objects(
            [_session_record(None, product=4567)],
            user_id=1,
            user_privacy_settings=_privacy_settings(),
        )

        assert activities[0]["activity"].tracker_model == "4567"

    def test_create_activity_objects_keeps_none_model(self):
        """A missing product stays None instead of the string 'None'."""
        activities = utils_fit.create_activity_objects(
            [_session_record(None, product=None)],
            user_id=1,
            user_privacy_settings=_privacy_settings(),
        )

        assert activities[0]["activity"].tracker_model is None

    def test_create_activity_objects_recomputes_hr_from_waypoints(self):
        """HR avg/max are recomputed from hr_waypoints, dropping zeros."""
        record = _session_record(None)
        # Populate hr_waypoints: one sensor-off zero, then real readings.
        record["hr_waypoints"] = [
            {"time": "2026-06-20T08:20:03", "hr": 0},
            {"time": "2026-06-20T08:20:10", "hr": 150},
            {"time": "2026-06-20T08:20:20", "hr": 160},
        ]
        # Stale device values that included the zero reading.
        record["session"]["avg_hr"] = 103
        record["session"]["max_hr"] = 160

        activities_list = utils_fit.create_activity_objects(
            [record],
            user_id=1,
            user_privacy_settings=_privacy_settings(),
        )

        activity = activities_list[0]["activity"]
        # Zeros excluded: mean([150, 160]) = 155, max = 160.
        assert activity.average_hr == 155
        assert activity.max_hr == 160
