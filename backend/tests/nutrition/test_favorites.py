"""Router + crud tests for the repeat-foods (favorites) endpoint."""

import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

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


def _row(log_id, name, **kwargs):
    defaults = {
        "id": log_id,
        "product_name": name,
        "calories": 100.0,
        "protein": 10.0,
        "carbs": 20.0,
        "fat": 5.0,
        "portion_g": 250.0,
        "off_barcode": None,
        "date": datetime.date(2026, 10, 29),
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


class TestFavoritesEndpoint:
    @patch("nutrition.router.nutrition_crud.recent_foods")
    def test_returns_crud_rows(self, mock_recent, mock_db) -> None:
        mock_recent.return_value = [
            {
                "product_name": "Кофе с молоком",
                "calories": 120.0,
                "protein": 6.0,
                "carbs": 12.0,
                "fat": 5.0,
                "portion_g": 250.0,
                "off_barcode": None,
                "last_logged": datetime.date(2026, 10, 29),
                "times_logged": 7,
            }
        ]
        client = TestClient(_build_app(mock_db))

        response = client.get(
            "/nutrition/favorites?query=%D0%BA%D0%BE&limit=8",
            headers={"Authorization": "Bearer x"},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["product_name"] == "Кофе с молоком"
        assert data[0]["times_logged"] == 7
        mock_recent.assert_called_once_with(1, "ко", 8, mock_db)

    @patch("nutrition.router.nutrition_crud.recent_foods")
    def test_empty_query_allowed(self, mock_recent, mock_db) -> None:
        mock_recent.return_value = []
        client = TestClient(_build_app(mock_db))

        response = client.get("/nutrition/favorites", headers={"Authorization": "Bearer x"})

        assert response.status_code == 200
        assert response.json() == []


class TestRecentFoodsCrud:
    def test_dedupes_by_name_latest_first(self, mock_db) -> None:
        import nutrition.crud as nutrition_crud

        rows = [
            _row(3, "Кофе с молоком", calories=130.0),
            _row(2, "КОФЕ С МОЛОКОМ", calories=120.0),
            _row(1, "Кофе черный", calories=5.0),
        ]
        scalars = MagicMock()
        scalars.all.return_value = rows
        mock_db.scalars.return_value = scalars

        out = nutrition_crud.recent_foods(1, "кофе", 8, mock_db)

        assert [r["product_name"] for r in out] == ["Кофе с молоком", "Кофе черный"]
        assert out[0]["calories"] == 130.0
        assert out[0]["times_logged"] == 2
