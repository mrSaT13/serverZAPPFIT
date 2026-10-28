"""Router tests for the nutrition trend (charts) endpoint."""

import datetime
from datetime import date as datetime_date
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient


def _build_app(mock_db):
    import auth.dependencies as auth_deps
    import core.database as core_db
    import nutrition.router as nutrition_router

    app = FastAPI()
    app.include_router(nutrition_router.router, prefix="/nutrition")

    app.dependency_overrides[auth_deps.check_auth_scopes] = lambda: None
    app.dependency_overrides[auth_deps.get_user_id_from_auth] = lambda: 1
    app.dependency_overrides[core_db.get_db] = lambda: mock_db
    return app


class TestTrendEndpoint:
    @patch("nutrition.router.nutrition_crud.daily_totals")
    def test_days_from_crud(self, mock_totals, mock_db) -> None:
        client = TestClient(_build_app(mock_db))
        mock_totals.return_value = [
            {"date": datetime_date(2026, 10, 1), "calories": 2000.0, "protein": 100.0, "carbs": 220.0, "fat": 70.0},
            {"date": datetime_date(2026, 10, 2), "calories": 1800.0, "protein": 90.0, "carbs": 200.0, "fat": 60.0},
        ]

        response = client.get(
            "/nutrition/trend?date_from=2026-10-01&date_to=2026-10-02",
            headers={"Authorization": "Bearer x"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["date_from"] == "2026-10-01"
        assert data["date_to"] == "2026-10-02"
        assert len(data["days"]) == 2
        assert data["days"][0]["calories"] == 2000.0
        # The activities aggregation degrades to None on a mock db session.
        assert data["days"][0]["burned_calories"] is None

    @patch("nutrition.router.nutrition_crud.daily_totals")
    def test_default_range_is_30_days(self, mock_totals, mock_db) -> None:
        client = TestClient(_build_app(mock_db))
        mock_totals.return_value = []

        response = client.get("/nutrition/trend", headers={"Authorization": "Bearer x"})

        assert response.status_code == 200
        called_from, called_to = mock_totals.call_args.args[1:3]
        assert datetime_date.fromisoformat(called_to) == datetime_date.today()
        assert datetime_date.fromisoformat(called_to) - datetime_date.fromisoformat(called_from) == datetime.timedelta(
            days=29
        )

    def test_inverted_range_rejected(self, mock_db) -> None:
        client = TestClient(_build_app(mock_db))
        response = client.get(
            "/nutrition/trend?date_from=2026-10-02&date_to=2026-10-01",
            headers={"Authorization": "Bearer x"},
        )
        assert response.status_code == 400

    def test_range_over_366_days_rejected(self, mock_db) -> None:
        client = TestClient(_build_app(mock_db))
        response = client.get(
            "/nutrition/trend?date_from=2024-01-01&date_to=2026-01-01",
            headers={"Authorization": "Bearer x"},
        )
        assert response.status_code == 400
