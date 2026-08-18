from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient


def _build_app(mock_db):
    import activities.activity_summaries.router as router
    import auth.dependencies as auth_deps
    import core.database as core_db

    app = FastAPI()
    app.include_router(router.router, prefix="/activities_summaries")

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


class TestReadWeeklySummary:
    @patch("activities.activity_summaries.router.summary_crud.get_weekly_summary")
    def test_weekly_summary_success(self, mock_get, mock_db):
        client = TestClient(_build_app(mock_db))
        from activities.activity_summaries.schema import WeeklySummaryResponse

        mock_get.return_value = WeeklySummaryResponse(breakdown=[], type_breakdown=None)

        response = client.get(
            "/activities_summaries/week?target_date_str=2024-01-15",
            headers={"Authorization": "Bearer x"},
        )
        assert response.status_code == 200


class TestReadMonthlySummary:
    @patch("activities.activity_summaries.router.summary_crud.get_monthly_summary")
    def test_monthly_summary_success(self, mock_get, mock_db):
        client = TestClient(_build_app(mock_db))
        from activities.activity_summaries.schema import MonthlySummaryResponse

        mock_get.return_value = MonthlySummaryResponse(breakdown=[], type_breakdown=None)

        response = client.get(
            "/activities_summaries/month?target_date_str=2024-01-15",
            headers={"Authorization": "Bearer x"},
        )
        assert response.status_code == 200


class TestReadYearlySummary:
    @patch("activities.activity_summaries.router.summary_crud.get_yearly_summary")
    def test_yearly_summary_success(self, mock_get, mock_db):
        client = TestClient(_build_app(mock_db))
        from activities.activity_summaries.schema import YearlySummaryResponse

        mock_get.return_value = YearlySummaryResponse(breakdown=[], type_breakdown=None)

        response = client.get(
            "/activities_summaries/year?year=2024",
            headers={"Authorization": "Bearer x"},
        )
        assert response.status_code == 200


class TestReadLifetimeSummary:
    @patch("activities.activity_summaries.router.summary_crud.get_lifetime_summary")
    def test_lifetime_summary_success(self, mock_get, mock_db):
        client = TestClient(_build_app(mock_db))
        from activities.activity_summaries.schema import LifetimeSummaryResponse

        mock_get.return_value = LifetimeSummaryResponse(breakdown=[], type_breakdown=None)

        response = client.get("/activities_summaries/lifetime", headers={"Authorization": "Bearer x"})
        assert response.status_code == 200
