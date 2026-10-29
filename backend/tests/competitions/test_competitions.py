"""Tests for competitions (races) + the web dashboard readiness snapshot."""

from datetime import date, timedelta
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

import competitions.crud as competitions_crud
import competitions.models as competitions_models
import competitions.schema as competitions_schema
import core.routes  # noqa: F401 — registers every model so ORM mappers initialise


def _competition(competition_id: int = 5, **overrides) -> competitions_models.Competition:
    fields = {
        "id": competition_id,
        "user_id": 1,
        "name": "Городской полумарафон",
        "competition_date": date.today() + timedelta(days=28),
        "distance_km": 21.1,
        "note": None,
        "status": "upcoming",
        "place": None,
        "total_participants": None,
        "result_time_s": None,
    }
    fields.update(overrides)
    return competitions_models.Competition(**fields)


def _db() -> MagicMock:
    return MagicMock()


class TestCrud:
    def test_create_returns_row(self) -> None:
        db = _db()
        payload = competitions_schema.CompetitionCreate(name="Марафон", competition_date="2026-12-06", distance_km=42.2)

        row = competitions_crud.create_competition(1, payload, db)

        assert row.user_id == 1
        assert row.name == "Марафон"
        assert row.status == "upcoming"
        db.add.assert_called_once()
        db.commit.assert_called_once()

    def test_get_404_for_missing_row(self) -> None:
        db = _db()
        db.scalars.return_value.first.return_value = None
        with pytest.raises(HTTPException) as err:
            competitions_crud.get_competition(1, 777, db)
        assert err.value.status_code == 404

    def test_get_scoped_to_owner(self) -> None:
        db = _db()
        db.scalars.return_value.first.return_value = None
        with pytest.raises(HTTPException):
            competitions_crud.get_competition(2, 5, db)

    def test_list_returns_rows(self) -> None:
        db = _db()
        db.scalars.return_value.all.return_value = [_competition()]
        rows = competitions_crud.list_competitions(1, db)
        assert len(rows) == 1

    def test_list_with_status_filter(self) -> None:
        db = _db()
        db.scalars.return_value.all.return_value = []
        rows = competitions_crud.list_competitions(1, db, status_filter="completed")
        assert rows == []

    def test_delete_removes_row(self) -> None:
        db = _db()
        db.scalars.return_value.first.return_value = _competition()
        competitions_crud.delete_competition(1, 5, db)
        db.delete.assert_called_once()

    def test_next_returns_earliest_upcoming(self) -> None:
        db = _db()
        db.scalars.return_value.first.return_value = _competition()
        row = competitions_crud.get_next_competition(1, db)
        assert row is not None
        assert row.status == "upcoming"

    def test_next_returns_none_when_no_upcoming(self) -> None:
        db = _db()
        db.scalars.return_value.first.return_value = None
        assert competitions_crud.get_next_competition(1, db) is None


class TestReadiness:
    def _snapshot(self, distances_m: list[int], competition: competitions_models.Competition):
        db = _db()
        db.scalars.return_value.all.return_value = list(distances_m)
        return competitions_crud.readiness_snapshot(1, competition, db)

    def test_half_marathon_thresholds(self) -> None:
        expected = competitions_schema.CompetitionStatus
        assert expected

        row = _competition(distance_km=21.1)
        snap = self._snapshot([45_000] * 4, row)  # 45 km/week → full readiness
        assert snap.required_weekly_km == 45
        assert snap.readiness == 1.0
        assert snap.avg_weekly_km == 45.0

    def test_5k_threshold_and_fractional_readiness(self) -> None:
        row = _competition(distance_km=5)
        snap = self._snapshot([10_000], row)  # 2.5 km/week of 20 expected
        assert snap.required_weekly_km == 20
        assert abs(snap.readiness - 0.125) < 1e-9

    def test_distance_tiers(self) -> None:
        db = _db()
        db.scalars.return_value.all.return_value = []

        tiers = {
            5.0: 20,
            10.0: 30,
            15.0: 45,
            21.0975: 45,
            21.5: 45,
            42.2: 60,
        }
        for distance, required in tiers.items():
            snap = competitions_crud.readiness_snapshot(1, _competition(distance_km=distance), db)
            assert snap.required_weekly_km == required, distance

    def test_days_left_clamped_to_zero_for_past_date(self) -> None:
        row = _competition(competition_date=date.today() - timedelta(days=3))
        snap = self._snapshot([], row)
        assert snap.days_left == 0

    def test_no_activities_means_zero_readiness(self) -> None:
        row = _competition()
        snap = self._snapshot([], row)
        assert snap.readiness == 0.0
        assert snap.avg_weekly_km == 0.0

    def test_null_distance_treated_as_zero(self) -> None:
        row = _competition()
        snap = self._snapshot([None, 10_000], row)  # type: ignore[list-item]
        assert snap.avg_weekly_km == 2.5


class TestRouter:
    def _client(self, db: MagicMock, user_id: int = 1) -> TestClient:
        import auth.dependencies as auth_dependencies
        import competitions.router as competitions_router
        import core.database as core_database

        app = FastAPI()
        app.include_router(competitions_router.router, prefix="/competitions")
        app.dependency_overrides[auth_dependencies.check_auth_scopes] = lambda: None
        app.dependency_overrides[auth_dependencies.get_user_id_from_auth] = lambda: user_id
        app.dependency_overrides[core_database.get_db] = lambda: db
        return TestClient(app)

    def test_next_with_no_competition_returns_null(self) -> None:
        db = _db()
        db.scalars.return_value.first.return_value = None
        resp = self._client(db).get("/competitions/next")
        assert resp.status_code == 200
        assert resp.json()["competition"] is None

    def test_next_includes_readiness(self) -> None:
        db = _db()
        today = date.today()
        db.scalars.return_value.first.return_value = _competition(competition_date=today + timedelta(days=7))
        db.scalars.return_value.all.return_value = [30_000, 30_000]
        resp = self._client(db).get("/competitions/next")
        assert resp.status_code == 200
        body = resp.json()
        assert body["competition"]["name"] == "Городской полумарафон"
        assert body["days_left"] == 7
        assert body["readiness"] > 0

    def test_list_endpoint(self) -> None:
        db = _db()
        db.scalars.return_value.all.return_value = [_competition()]
        resp = self._client(db).get("/competitions")
        assert resp.status_code == 200
        assert resp.json()[0]["name"] == "Городской полумарафон"

    def test_get_404(self) -> None:
        db = _db()
        db.scalars.return_value.first.return_value = None
        resp = self._client(db).get("/competitions/777")
        assert resp.status_code == 404
