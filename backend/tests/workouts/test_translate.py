"""Router tests for the on-demand exercise translation endpoint."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient


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


def _row(translations=None, tips=None):
    return SimpleNamespace(
        wger_id=9,
        translations=translations
        if translations is not None
        else {"en": {"name": "Bench Press", "description": "<p>Lie down.</p>"}},
        tips=tips if tips is not None else {"en": ["Keep your back flat."]},
    )


def _scalars(first):
    scalars = MagicMock()
    scalars.first.return_value = first
    return scalars


class TestTranslateEndpoint:
    @patch("workouts.router.nutrition_ai.get_ai_settings")
    def test_requires_configuration(self, mock_settings, mock_db) -> None:
        mock_settings.return_value = MagicMock(configured=False)
        mock_db.scalars.return_value = _scalars(_row())

        response = TestClient(_build_app(mock_db)).post(
            "/workouts/exercises/9/translate",
            json={},
            headers={"Authorization": "Bearer x"},
        )

        assert response.status_code == 503

    @patch("workouts.router.nutrition_ai.get_ai_settings")
    def test_unknown_exercise_is_404(self, mock_settings, mock_db) -> None:
        mock_settings.return_value = MagicMock(configured=True)
        mock_db.scalars.return_value = _scalars(None)

        response = TestClient(_build_app(mock_db)).post(
            "/workouts/exercises/999999/translate",
            json={},
            headers={"Authorization": "Bearer x"},
        )

        assert response.status_code == 404

    @patch("workouts.router.nutrition_ai.chat_completion", new_callable=AsyncMock)
    @patch("workouts.router.nutrition_ai.get_ai_settings")
    def test_success_parses_blocks(self, mock_settings, mock_chat, mock_db) -> None:
        mock_settings.return_value = MagicMock(configured=True, base_url="http://x", api_key="k", model="m")
        mock_db.scalars.return_value = _scalars(_row())
        mock_chat.return_value = "DESCRIPTION: Лягте на скамью.\nTIP: Держите спину ровно."

        response = TestClient(_build_app(mock_db)).post(
            "/workouts/exercises/9/translate",
            json={"language": "ru"},
            headers={"Authorization": "Bearer x"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["wger_id"] == 9
        assert data["language"] == "ru"
        assert data["description"] == "Лягте на скамью."
        assert data["tip"] == "Держите спину ровно."

    @patch("workouts.router.nutrition_ai.chat_completion", new_callable=AsyncMock)
    @patch("workouts.router.nutrition_ai.get_ai_settings")
    def test_empty_source_returns_empty(self, mock_settings, mock_chat, mock_db) -> None:
        mock_settings.return_value = MagicMock(configured=True, base_url="http://x", api_key="k", model="m")
        mock_db.scalars.return_value = _scalars(_row(translations={}, tips={}))

        response = TestClient(_build_app(mock_db)).post(
            "/workouts/exercises/9/translate",
            json={},
            headers={"Authorization": "Bearer x"},
        )

        assert response.status_code == 200
        assert response.json()["description"] == ""
        mock_chat.assert_not_called()

    @patch("workouts.router.nutrition_ai.chat_completion", new_callable=AsyncMock)
    @patch("workouts.router.nutrition_ai.get_ai_settings")
    def test_provider_error_maps_to_502(self, mock_settings, mock_chat, mock_db) -> None:
        import nutrition.ai as nutrition_ai

        mock_settings.return_value = MagicMock(configured=True, base_url="http://x", api_key="k", model="m")
        mock_db.scalars.return_value = _scalars(_row())
        mock_chat.side_effect = nutrition_ai.AiAssistantError("down")

        response = TestClient(_build_app(mock_db)).post(
            "/workouts/exercises/9/translate",
            json={},
            headers={"Authorization": "Bearer x"},
        )

        assert response.status_code == 502
