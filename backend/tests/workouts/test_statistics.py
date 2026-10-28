"""Tests for the workouts statistics aggregation (charts API)."""

from datetime import date as datetime_date
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException, status

import workouts.crud as workouts_crud
import workouts.models as workouts_models
import workouts.schema as workouts_schema


class TestWeekStart:
    def test_monday_stays_put(self) -> None:
        assert workouts_crud.week_start(datetime_date(2026, 10, 19)) == datetime_date(2026, 10, 19)

    def test_sunday_snaps_to_monday(self) -> None:
        assert workouts_crud.week_start(datetime_date(2026, 10, 25)) == datetime_date(2026, 10, 19)


def _session(day: datetime_date, sets: list[tuple[float | None, int | None, bool]]) -> MagicMock:
    row = MagicMock(spec=workouts_models.WorkoutSession)
    row.date = day
    row.sets = [
        MagicMock(spec=workouts_models.WorkoutSetLog, weight_kg=w, reps=r, completed=done) for (w, r, done) in sets
    ]
    return row


class TestWeeklyStatistics:
    @patch.object(workouts_crud, "list_sessions")
    def test_buckets_by_iso_week_and_skips_incomplete(self, mock_list, mock_db) -> None:
        mock_list.return_value = [
            _session(datetime_date(2026, 10, 19), [(100.0, 10, True), (80.0, 8, False)]),
            _session(datetime_date(2026, 10, 21), [(120.0, 5, True)]),
            _session(datetime_date(2026, 10, 27), [(60.0, 12, True)]),
        ]

        result = workouts_crud.weekly_statistics(1, "2026-10-01", "2026-10-31", mock_db)

        assert len(result.weeks) == 2
        week1 = result.weeks[0]
        assert week1.week_start == datetime_date(2026, 10, 19)
        assert week1.sessions == 2
        assert week1.sets == 2
        assert week1.reps == 15
        assert week1.volume_kg == 100.0 * 10 + 120.0 * 5
        week2 = result.weeks[1]
        assert week2.week_start == datetime_date(2026, 10, 26)
        assert week2.sessions == 1
        assert week2.volume_kg == 60.0 * 12

        assert result.total_sessions == 3
        assert result.total_sets == 3
        assert result.total_reps == 27
        assert result.total_volume_kg == 1000.0 + 600.0 + 720.0

    @patch.object(workouts_crud, "list_sessions")
    def test_empty_range(self, mock_list, mock_db) -> None:
        mock_list.return_value = []
        result = workouts_crud.weekly_statistics(1, None, None, mock_db)
        assert result.weeks == []
        assert result.total_sessions == 0

    def test_inverted_range_rejected(self, mock_db) -> None:
        with pytest.raises(HTTPException) as exc:
            workouts_crud.weekly_statistics(1, "2026-10-31", "2026-10-01", mock_db)
        assert exc.value.status_code == status.HTTP_400_BAD_REQUEST

    def test_range_over_366_days_rejected(self, mock_db) -> None:
        with pytest.raises(HTTPException) as exc:
            workouts_crud.weekly_statistics(1, "2024-01-01", "2026-01-01", mock_db)
        assert exc.value.status_code == status.HTTP_400_BAD_REQUEST

    @patch.object(workouts_crud, "list_sessions")
    def test_schema_roundtrip(self, mock_list, mock_db) -> None:
        mock_list.return_value = [
            _session(datetime_date(2026, 10, 20), [(50.0, 10, True)]),
        ]
        result = workouts_crud.weekly_statistics(1, "2026-10-01", "2026-10-31", mock_db)
        dumped = workouts_schema.WorkoutStatistics.model_validate(result.model_dump())
        assert dumped.weeks[0].week_start == datetime_date(2026, 10, 19)
