"""Tests for the user training inventory (weights fed to the AI planner)."""

from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

import core.routes  # noqa: F401 — registers every model so ORM mappers initialise
import workouts.equipment_crud as equipment_crud
import workouts.equipment_models as equipment_models
import workouts.equipment_schema as equipment_schema


def _row(item_id: int = 5) -> equipment_models.UserEquipment:
    return equipment_models.UserEquipment(
        id=item_id,
        user_id=1,
        name="Гантели 10 кг",
        equipment_id=None,
        weight_kg=Decimal("10.00"),
        quantity=1,
    )


def _db():
    return MagicMock()


class TestCrud:
    def test_create_returns_row(self) -> None:
        db = _db()
        payload = equipment_schema.EquipmentCreate(name="Штанга 20 кг", weight_kg=Decimal("20"), quantity=1)

        row = equipment_crud.create_equipment(1, payload, db)

        assert row.user_id == 1
        assert row.name == "Штанга 20 кг"
        db.add.assert_called_once()
        db.commit.assert_called_once()

    def test_get_404_for_missing_row(self) -> None:
        db = _db()
        db.scalars.return_value.first.return_value = None
        with pytest.raises(HTTPException) as err:
            equipment_crud.get_equipment(1, 777, db)
        assert err.value.status_code == 404

    def test_list_returns_rows(self) -> None:
        db = _db()
        db.scalars.return_value.all.return_value = [_row()]
        rows = equipment_crud.list_equipment(1, db)
        assert len(rows) == 1

    def test_delete_removes_row(self) -> None:
        db = _db()
        db.scalars.return_value.first.return_value = _row()
        equipment_crud.delete_equipment(1, 5, db)
        db.delete.assert_called_once()
        db.commit.assert_called_once()


def _client(mock_db) -> TestClient:
    import auth.dependencies as auth_deps
    import core.database as core_db
    import workouts.router as workouts_router

    app = FastAPI()
    app.include_router(workouts_router.router, prefix="/workouts")
    app.dependency_overrides[auth_deps.check_auth_scopes] = lambda: None
    app.dependency_overrides[auth_deps.get_user_id_from_auth] = lambda: 1
    app.dependency_overrides[core_db.get_db] = lambda: mock_db
    return TestClient(app)


class TestRouter:
    def test_list_endpoint(self) -> None:
        db = _db()
        db.scalars.return_value.all.return_value = [_row()]

        response = _client(db).get("/workouts/equipment", headers={"Authorization": "Bearer x"})

        assert response.status_code == 200
        data = response.json()
        assert data[0]["name"] == "Гантели 10 кг"

    def test_create_endpoint(self) -> None:
        db = _db()
        # TestClient runs the real(crud) create — emulate the DB assigning the
        # id on refresh, since EquipmentRead requires it.
        db.refresh.side_effect = lambda row: setattr(row, "id", 5)

        response = _client(db).post(
            "/workouts/equipment",
            headers={"Authorization": "Bearer x"},
            json={"name": "Гантели 10 кг", "equipment_id": None, "weight_kg": "10", "quantity": 1},
        )

        assert response.status_code == 201, response.text
        assert response.json()["name"] == "Гантели 10 кг"

    def test_delete_endpoint_404(self) -> None:
        db = _db()
        db.scalars.return_value.first.return_value = None
        response = _client(db).delete("/workouts/equipment/777", headers={"Authorization": "Bearer x"})
        assert response.status_code == 404
