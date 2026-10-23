"""PMC (Performance Management Chart) computation for activities.

Computes daily TSS from activities and applies the standard
exponential-smoothing model: CTL over 42 days (chronic load),
ATL over 7 days (acute load), TSB = CTL - ATL (form).

TSS source priority per activity: explicit ``tss`` > ``hr_tss`` >
``trimp`` > ``suffer_score`` > duration-based heuristic scaled by
workout RPE (same fallback the frontend used before the endpoint
existed).
"""

from collections.abc import Iterable
from datetime import date, timedelta

import activities.activity.schema as activities_schema

_CTL_DAYS = 42
_ATL_DAYS = 7

_MIN_TSS_PER_HOUR = 20
_MAX_TSS_PER_HOUR = 150

_RPE_TO_TSS_FACTOR = 50


def estimate_activity_tss(activity) -> int:
    """Estimate training stress for a single activity row.

    Args:
        activity: ORM activity (or projection Row) exposing ``tss``,
            ``hr_tss``, ``trimp``, ``suffer_score``, ``workout_rpe``,
            ``total_timer_time`` and ``total_elapsed_time`` (seconds).

    Returns:
        Non-negative TSS estimate.
    """
    for value in (activity.tss, activity.hr_tss, activity.trimp, activity.suffer_score):
        if value is not None:
            return max(0, round(float(value)))

    seconds = activity.total_timer_time or activity.total_elapsed_time
    hours = float(seconds or 0) / 3600
    if hours <= 0:
        return 0

    rpe_factor = float(activity.workout_rpe) / _RPE_TO_TSS_FACTOR if activity.workout_rpe else 1
    per_hour = min(_MAX_TSS_PER_HOUR, max(_MIN_TSS_PER_HOUR, 60 * rpe_factor))
    return round(hours * per_hour)


def _daily_tss(activities: Iterable) -> dict[date, int]:
    """Aggregate estimated TSS by local calendar day of start."""
    daily: dict[date, int] = {}
    for activity in activities:
        start_time = getattr(activity, "start_time", None)
        if start_time is None:
            continue
        day = start_time.date() if hasattr(start_time, "date") else None
        if day is None:
            continue
        tss = estimate_activity_tss(activity)
        if tss > 0:
            daily[day] = daily.get(day, 0) + tss
    return daily


def compute_training_metrics(
    activities: Iterable,
    *,
    today: date,
    days: int,
) -> activities_schema.TrainingMetrics:
    """Compute CTL/ATL/TSB over ``days`` days ending on ``today``.

    Smoothing starts from zero at the beginning of the window, so
    ``today - days`` days of history are used to warm up CTL before
    the reported series begins.

    Args:
        activities: Activity rows within the warm-up window.
        today: Current date (series ends here).
        days: Length of the reported series (7..365).

    Returns:
        ``TrainingMetrics`` schema with the trailing ``days`` points.
    """
    start_date = today - timedelta(days=days + 90)
    daily = _daily_tss(activities)

    ctl = 0.0
    atl = 0.0
    points: list[activities_schema.PmcPoint] = []
    tsb_today = None
    tss_today = daily.get(today, 0)

    current = start_date
    while current <= today:
        tss = daily.get(current, 0)
        ctl += (tss - ctl) * (2 / (_CTL_DAYS + 1))
        atl += (tss - atl) * (2 / (_ATL_DAYS + 1))
        if current > today - timedelta(days=days):
            points.append(activities_schema.PmcPoint(date=current, tss=tss))
        tsb_today = ctl - atl
        current += timedelta(days=1)

    return activities_schema.TrainingMetrics(
        ctl=ctl,
        atl=atl,
        tsb=tsb_today or 0.0,
        tss_today=tss_today,
        points=points,
    )
