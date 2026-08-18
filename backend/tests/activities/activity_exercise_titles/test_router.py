from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient


def _build_app(mock_db):
    import activities.activity_exercise_titles.router as router
    import auth.dependencies as auth_deps
    import core.database as core_db

    app = FastAPI()
    app.include_router(router.router, prefix="/activities_exercise_titles")

    def _mock():
        return None

    def _uid():
        return 1

    app.dependency_overrides[auth_deps.check_scopes] = _mock
    app.dependency_overrides[auth_deps.get_sub_from_access_token] = _uid
    app.dependency_overrides[auth_deps.validate_access_token_or_api_key] = lambda: auth_deps.AuthContext(
        user_id=1, scopes=["*"], auth_type="jwt"
    )
    app.dependency_overrides[auth_deps.check_auth_scopes] = _mock
    app.dependency_overrides[auth_deps.get_user_id_from_auth] = _uid
    app.dependency_overrides[core_db.get_db] = lambda: mock_db
    return app


class TestReadExerciseTitles:
    @patch("activities.activity_exercise_titles.router.activity_exercise_titles_crud.get_activity_exercise_titles")
    def test_read_titles_success(self, mock_get, mock_db):
        client = TestClient(_build_app(mock_db))
        mock_get.return_value = []

        response = client.get("/activities_exercise_titles/all", headers={"Authorization": "Bearer x"})
        assert response.status_code == 200
