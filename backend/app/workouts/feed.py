"""Publish strength sessions to the activity feed (opt-in).

When a user enables ``publish_workouts_in_feed`` in their privacy settings,
every newly logged workout session is mirrored as a Strength training
activity (type 19) so it shows up in the home feed with the standard card,
metrics and comments. The session keeps ``activity_id`` pointing back at the
feed entry: deleting the session removes the activity, deleting the activity
(e.g. from the feed menu) just clears the link.

Design notes:
- Best-effort: a feed failure is logged but never fails the session save.
- The activity mirrors the user's privacy choices (default visibility and
  the ``hide_*`` flags) so publishing cannot leak more than a normal activity.
"""

from datetime import UTC, datetime, timedelta
from datetime import time as time_type
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

import activities.activity.models as activities_models
import core.logger as core_logger
import users.users.models as users_models
import users.users_privacy_settings.models as privacy_models
import workouts.models as workouts_models

# utils.ACTIVITY_NAME_TO_ID canonical id for strength training.
ACTIVITY_TYPE_STRENGTH = 19

_VISIBILITY_TO_INT = {"public": 0, "followers": 1, "private": 2}

# Feed copy for the two UI languages; other locales fall back to English.
_LABELS: dict[str, dict[str, str]] = {
    "ru": {
        "name": "Силовая тренировка",
        "summary": "{exercises} упражнений · {sets} подходов · {volume} кг",
    },
    "en": {
        "name": "Strength workout",
        "summary": "{exercises} exercises · {sets} sets · {volume} kg",
    },
}


def _labels(preferred_language: str | None) -> dict[str, str]:
    lang = (preferred_language or "en").split("-")[0]
    return _LABELS.get(lang, _LABELS["en"])


def _privacy_settings(user_id: int, db: Session) -> privacy_models.UsersPrivacySettings | None:
    stmt = select(privacy_models.UsersPrivacySettings).where(privacy_models.UsersPrivacySettings.user_id == user_id)
    return db.execute(stmt).scalar_one_or_none()


def _session_summary(session_row: workouts_models.WorkoutSession, labels: dict[str, str]) -> str:
    """Compact "N exercises · M sets · V kg" line for the feed description."""
    completed = [s for s in session_row.sets if s.completed]
    exercises = {s.exercise_name for s in completed}
    volume = sum((s.weight_kg or 0) * (s.reps or 0) for s in completed)
    return labels["summary"].format(exercises=len(exercises), sets=len(completed), volume=round(volume))


def publish_session_activity(user_id: int, session_row: workouts_models.WorkoutSession, db: Session) -> None:
    """Mirror a workout session into the feed when the user opted in."""
    privacy = _privacy_settings(user_id, db)
    if privacy is None or not privacy.publish_workouts_in_feed:
        return
    if session_row.activity_id is not None:
        return  # already published (idempotent guard)

    user = db.get(users_models.Users, user_id)
    labels = _labels(getattr(user, "preferred_language", None))

    name = None
    if session_row.plan_id is not None:
        plan = db.get(workouts_models.WorkoutPlan, session_row.plan_id)
        name = plan.name if plan else None
    if not name:
        name = (session_row.comment or "").strip() or None
    description_parts = [p for p in [(session_row.comment or "").strip()] if p and p != name]
    description_parts.append(_session_summary(session_row, labels))
    description = "\n".join(description_parts)[:2500]

    # Sessions carry a date only — anchor at noon UTC so the feed shows the
    # right day regardless of the viewer's timezone.
    start = datetime.combine(session_row.date, time_type(12, 0), tzinfo=UTC)
    duration = timedelta(minutes=session_row.duration_min or 0)
    end = start + duration if session_row.duration_min else start
    seconds = float(session_row.duration_min * 60) if session_row.duration_min else 0.0

    activity = activities_models.Activity(
        user_id=user_id,
        name=(name or labels["name"])[:250],
        description=description,
        distance=0,
        activity_type=ACTIVITY_TYPE_STRENGTH,
        start_time=start,
        end_time=end,
        total_elapsed_time=seconds,
        total_timer_time=seconds,
        calories=round(session_row.calories) if session_row.calories else None,
        visibility=_VISIBILITY_TO_INT.get(privacy.default_activity_visibility or "public", 0),
        created_at=datetime.now(UTC),
        is_hidden=False,
        # Mirror the user's per-metric hide preferences (no DB defaults on
        # some of these columns, so they are always set explicitly).
        hide_start_time=privacy.hide_activity_start_time,
        hide_location=privacy.hide_activity_location,
        hide_map=privacy.hide_activity_map,
        hide_hr=privacy.hide_activity_hr,
        hide_power=privacy.hide_activity_power,
        hide_cadence=privacy.hide_activity_cadence,
        hide_elevation=privacy.hide_activity_elevation,
        hide_speed=privacy.hide_activity_speed,
        hide_pace=privacy.hide_activity_pace,
        hide_laps=privacy.hide_activity_laps,
        hide_workout_sets_steps=privacy.hide_activity_workout_sets_steps,
        hide_gear=privacy.hide_activity_gear,
        import_info={"import_source": "zapfit_workout", "workout_session_id": session_row.id},
    )
    db.add(activity)
    db.flush()
    session_row.activity_id = activity.id
    db.commit()
    db.refresh(session_row)
    core_logger.print_to_log(
        f"Published workout session {session_row.id} to feed as activity {activity.id}",
    )


def delete_published_activity(activity_id: int, db: Session) -> None:
    """Remove the feed activity a session published (session is being deleted)."""
    try:
        db.execute(delete(activities_models.Activity).where(activities_models.Activity.id == activity_id))
        db.commit()
    except Exception as e:
        db.rollback()
        core_logger.print_to_log(f"Feed cleanup for activity {activity_id} failed: {e}", "error", exc=e)


def published_activity_ids(user_id: int, db: Session) -> list[int]:
    """Feed activity ids published from this user's sessions (diagnostics/tests)."""
    stmt = select(workouts_models.WorkoutSession.activity_id).where(
        workouts_models.WorkoutSession.user_id == user_id,
        workouts_models.WorkoutSession.activity_id.is_not(None),
    )
    return [row for row in db.scalars(stmt).all() if row is not None]


def feed_settings_snapshot(user_id: int, db: Session) -> dict[str, Any] | None:
    """Privacy rows relevant to feed publishing (tests/diagnostics helper)."""
    privacy = _privacy_settings(user_id, db)
    if privacy is None:
        return None
    return {
        "publish_workouts_in_feed": privacy.publish_workouts_in_feed,
        "default_activity_visibility": privacy.default_activity_visibility,
    }
