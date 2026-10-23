"""Tests for the PMC (Performance Management Chart) computation."""

import types
from datetime import UTC, date, datetime, timedelta

import activities.activity.training_metrics as training_metrics


def _activity(
    start: datetime,
    *,
    tss=None,
    hr_tss=None,
    trimp=None,
    suffer_score=None,
    workout_rpe=None,
    total_timer_time=None,
    total_elapsed_time=None,
):
    return types.SimpleNamespace(
        start_time=start,
        tss=tss,
        hr_tss=hr_tss,
        trimp=trimp,
        suffer_score=suffer_score,
        workout_rpe=workout_rpe,
        total_timer_time=total_timer_time,
        total_elapsed_time=total_elapsed_time,
    )


class TestEstimateActivityTss:
    def test_explicit_tss_wins(self):
        a = _activity(
            datetime(2026, 1, 1, tzinfo=UTC),
            tss=100,
            hr_tss=50,
            trimp=30,
            suffer_score=20,
            total_timer_time=3600,
        )
        assert training_metrics.estimate_activity_tss(a) == 100

    def test_hr_tss_fallback(self):
        a = _activity(datetime(2026, 1, 1, tzinfo=UTC), hr_tss=50, trimp=30)
        assert training_metrics.estimate_activity_tss(a) == 50

    def test_trimp_fallback(self):
        a = _activity(datetime(2026, 1, 1, tzinfo=UTC), trimp=30)
        assert training_metrics.estimate_activity_tss(a) == 30

    def test_suffer_score_fallback(self):
        a = _activity(datetime(2026, 1, 1, tzinfo=UTC), suffer_score=25)
        assert training_metrics.estimate_activity_tss(a) == 25

    def test_duration_heuristic_default_rpe(self):
        a = _activity(datetime(2026, 1, 1, tzinfo=UTC), total_timer_time=3600)
        assert training_metrics.estimate_activity_tss(a) == 60

    def test_duration_heuristic_rpe(self):
        a = _activity(
            datetime(2026, 1, 1, tzinfo=UTC),
            total_timer_time=3600,
            workout_rpe=100,
        )
        # per_hour = 60 * (100/50) = 120, clamped within [20, 150]
        assert training_metrics.estimate_activity_tss(a) == 120

    def test_negative_tss_clamped_to_zero(self):
        a = _activity(datetime(2026, 1, 1, tzinfo=UTC), tss=-10)
        assert training_metrics.estimate_activity_tss(a) == 0

    def test_zero_duration_with_no_metrics(self):
        a = _activity(datetime(2026, 1, 1, tzinfo=UTC))
        assert training_metrics.estimate_activity_tss(a) == 0


class TestComputeTrainingMetrics:
    def test_zero_activities_gives_zero_metrics(self):
        today = date(2026, 10, 20)
        r = training_metrics.compute_training_metrics([], today=today, days=30)
        assert r.ctl == 0.0
        assert r.atl == 0.0
        assert r.tsb == 0.0
        assert r.tss_today == 0
        assert len(r.points) == 30
        assert r.points[0].date == today - timedelta(days=29)
        assert r.points[-1].date == today
        assert all(p.tss == 0 for p in r.points)

    def test_series_length_and_last_day(self):
        today = date(2026, 10, 20)
        r = training_metrics.compute_training_metrics([], today=today, days=7)
        assert len(r.points) == 7
        assert r.points[-1].date == today

    def test_single_activity_today(self):
        today = date(2026, 10, 20)
        a = _activity(
            datetime.combine(today, datetime.min.time(), tzinfo=UTC),
            total_timer_time=3600,
        )
        r = training_metrics.compute_training_metrics([a], today=today, days=14)
        assert r.tss_today == 60
        # Same-day activity raises ATL above CTL, so TSB is negative.
        assert r.atl > r.ctl
        assert r.tsb < 0

    def test_explicit_tss_used_in_series(self):
        today = date(2026, 10, 20)
        a = _activity(
            datetime.combine(today, datetime.min.time(), tzinfo=UTC),
            tss=42,
        )
        r = training_metrics.compute_training_metrics([a], today=today, days=7)
        assert r.points[-1].tss == 42
        assert r.ctl > 0

    def test_decimal_timer_time(self):
        from decimal import Decimal

        today = date(2026, 10, 20)
        a = _activity(
            datetime.combine(today, datetime.min.time(), tzinfo=UTC),
            total_timer_time=Decimal("3600"),
        )
        r = training_metrics.compute_training_metrics([a], today=today, days=7)
        assert r.tss_today == 60
