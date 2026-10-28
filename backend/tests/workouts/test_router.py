"""Router tests for the workouts statistics and AI plan endpoints."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import workouts.ai_planner as workouts_ai_planner


def _build_app(mock_db):
    import auth.dependencies as auth_deps
    import core.database as core_db
    import workouts.router as workouts_router

    app = FastAPI()
    app.include_router(workouts_router.router, prefix="/workouts")

    app.dependency_overrides[auth_deps.check_auth_scopes] = lambda: None
    app.dependency_overrides[auth_deps.get_user_id_from_auth] = lambda: 1
    app.dependency_overrides[core_db.get_db] = lambda: mock_db
    return app


class TestStatisticsEndpoint:
    @patch("workouts.router.workouts_crud.weekly_statistics")
    def test_success(self, mock_stats, mock_db) -> None:
        import workouts.schema as workouts_schema

        client = TestClient(_build_app(mock_db))
        mock_stats.return_value = workouts_schema.WorkoutStatistics(
            date_from="2026-01-01",
            date_to="2026-03-31",
            total_sessions=2,
            total_volume_kg=1500.0,
            total_sets=8,
            total_reps=40,
            weeks=[
                workouts_schema.WorkoutStatisticsPoint(
                    week_start="2026-01-05", sessions=2, volume_kg=1500.0, sets=8, reps=40
                )
            ],
        )

        response = client.get(
            "/workouts/statistics?date_from=2026-01-01&date_to=2026-03-31",
            headers={"Authorization": "Bearer x"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_sessions"] == 2
        assert data["weeks"][0]["week_start"] == "2026-01-05"
        mock_stats.assert_called_once_with(1, "2026-01-01", "2026-03-31", mock_db)

    @patch("workouts.router.workouts_crud.weekly_statistics")
    def test_default_range(self, mock_stats, mock_db) -> None:
        import workouts.schema as workouts_schema

        client = TestClient(_build_app(mock_db))
        mock_stats.return_value = workouts_schema.WorkoutStatistics(date_from="2026-01-01", date_to="2026-01-31")

        response = client.get("/workouts/statistics", headers={"Authorization": "Bearer x"})

        assert response.status_code == 200
        assert mock_stats.call_args.args[1] is None
        assert mock_stats.call_args.args[2] is None


AI_DRAFT = {
    "name": "Грудь",
    "description": "База",
    "exercises": [
        {
            "day_label": "День 1",
            "name": "Жим лёжа",
            "muscle_group": "Chest",
            "wger_exercise_id": 9,
            "notes": None,
            "target_sets": 4,
            "target_reps": "8-12",
            "target_weight_kg": None,
            "rest_s": 90,
        }
    ],
    "model": "test-model",
}


class TestAiPlanEndpoints:
    @patch("workouts.router.nutrition_ai.get_ai_settings")
    def test_status(self, mock_settings, mock_db) -> None:
        client = TestClient(_build_app(mock_db))
        mock_settings.return_value = MagicMock(configured=True, enabled=True, model="m1")

        response = client.get("/workouts/ai/status", headers={"Authorization": "Bearer x"})

        assert response.status_code == 200
        assert response.json() == {"enabled": True, "configured": True, "model": "m1"}

    @patch("workouts.router.nutrition_ai.get_ai_settings")
    def test_plan_requires_configuration(self, mock_settings, mock_db) -> None:
        client = TestClient(_build_app(mock_db))
        mock_settings.return_value = MagicMock(configured=False)

        response = client.post(
            "/workouts/ai/plan",
            json={"prompt": "накачать грудь"},
            headers={"Authorization": "Bearer x"},
        )

        assert response.status_code == 503

    @patch("workouts.router.workouts_ai_planner.generate_plan", new_callable=AsyncMock)
    @patch("workouts.router.nutrition_ai.get_ai_settings")
    def test_plan_success(self, mock_settings, mock_generate, mock_db) -> None:
        import workouts.schema as workouts_schema

        client = TestClient(_build_app(mock_db))
        mock_settings.return_value = MagicMock(configured=True, enabled=True, model="m1")
        mock_generate.return_value = workouts_schema.AiPlanDraft.model_validate(AI_DRAFT)

        response = client.post(
            "/workouts/ai/plan",
            json={"prompt": "накачать грудные мышцы", "language": "ru"},
            headers={"Authorization": "Bearer x"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["exercises"][0]["name"] == "Жим лёжа"
        assert data["model"] == "test-model"

    @patch("workouts.router.workouts_ai_planner.generate_plan", new_callable=AsyncMock)
    @patch("workouts.router.nutrition_ai.get_ai_settings")
    def test_plan_provider_error_maps_to_502(self, mock_settings, mock_generate, mock_db) -> None:
        client = TestClient(_build_app(mock_db))
        mock_settings.return_value = MagicMock(configured=True, enabled=True, model="m1")
        mock_generate.side_effect = workouts_ai_planner.AiPlanError("bad reply")

        response = client.post(
            "/workouts/ai/plan",
            json={"prompt": "накачать грудные мышцы"},
            headers={"Authorization": "Bearer x"},
        )

        assert response.status_code == 502


@pytest.mark.parametrize("payload", [{"prompt": ""}, {"prompt": "x"}])
def test_plan_validates_prompt_length(mock_db, payload) -> None:
    client = TestClient(_build_app(mock_db))
    response = client.post(
        "/workouts/ai/plan",
        json=payload,
        headers={"Authorization": "Bearer x"},
    )
    assert response.status_code == 422
