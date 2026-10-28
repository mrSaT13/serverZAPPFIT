"""Tests for activity comments access rules."""

from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi import HTTPException

import activities.activity_comments.crud as comments_crud
import activities.activity_comments.schema as comment_schema

VISIBLE_ACTIVITY = SimpleNamespace(id=10, user_id=5)
_VISIBILITY_FN = "activities.activity_comments.crud.activity_crud.get_activity_by_id_from_user_id_or_has_visibility"


class TestGetComments:
    def test_visible_follower_can_read(self, mock_db):
        from tests._helpers.db import setup_mock_execute

        with patch(_VISIBILITY_FN, return_value=VISIBLE_ACTIVITY) as vis:
            comment = SimpleNamespace(id=1, activity_id=10, user_id=7)
            setup_mock_execute(mock_db, return_scalars_all=[comment])
            result = comments_crud.get_comments_by_activity_id(activity_id=10, token_user_id=7, db=mock_db)
        assert result == [comment]
        vis.assert_called_once_with(10, 7, mock_db)

    def test_invisible_activity_returns_404(self, mock_db):
        with patch(_VISIBILITY_FN, return_value=None), pytest.raises(HTTPException) as exc:
            comments_crud.get_comments_by_activity_id(activity_id=10, token_user_id=99, db=mock_db)
        assert exc.value.status_code == 404


class TestCreateComment:
    def test_visible_follower_can_comment(self, mock_db):
        data = comment_schema.ActivityCommentCreate(content="Nice ride!")

        def fake_model(**kwargs):
            return SimpleNamespace(**kwargs)

        with (
            patch(_VISIBILITY_FN, return_value=VISIBLE_ACTIVITY),
            patch("activities.activity_comments.models.ActivityComment", side_effect=fake_model),
        ):
            result = comments_crud.create_comment(activity_id=10, user_id=7, data=data, db=mock_db)
        assert result.activity_id == 10
        assert result.user_id == 7
        assert result.content == "Nice ride!"
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    def test_invisible_activity_returns_404(self, mock_db):
        data = comment_schema.ActivityCommentCreate(content="Hi")
        with patch(_VISIBILITY_FN, return_value=None), pytest.raises(HTTPException) as exc:
            comments_crud.create_comment(activity_id=10, user_id=99, data=data, db=mock_db)
        assert exc.value.status_code == 404


class TestDeleteComment:
    def test_activity_owner_can_delete_foreign_comment(self, mock_db):
        comment = SimpleNamespace(id=3, activity_id=10, user_id=7)
        mock_db.scalars.return_value.first.return_value = comment
        with patch(
            "activities.activity_comments.crud.activity_crud.get_activity_by_id_from_user_id",
            return_value=VISIBLE_ACTIVITY,
        ):
            comments_crud.delete_comment(comment_id=3, user_id=5, db=mock_db)
        mock_db.delete.assert_called_once_with(comment)

    def test_unrelated_user_gets_403(self, mock_db):
        comment = SimpleNamespace(id=3, activity_id=10, user_id=7)
        mock_db.scalars.return_value.first.return_value = comment
        with (
            patch(
                "activities.activity_comments.crud.activity_crud.get_activity_by_id_from_user_id",
                return_value=None,
            ),
            pytest.raises(HTTPException) as exc,
        ):
            comments_crud.delete_comment(comment_id=3, user_id=99, db=mock_db)
        assert exc.value.status_code == 403

    def test_missing_comment_returns_404(self, mock_db):
        mock_db.scalars.return_value.first.return_value = None
        with pytest.raises(HTTPException) as exc:
            comments_crud.delete_comment(comment_id=999, user_id=5, db=mock_db)
        assert exc.value.status_code == 404


class TestUpdateComment:
    def test_author_can_edit(self, mock_db):
        from tests._helpers.db import setup_mock_execute

        comment = SimpleNamespace(id=4, activity_id=10, user_id=7, content="old", updated_at=None)
        setup_mock_execute(mock_db, return_scalars_all=[])
        mock_db.scalars.return_value.first.return_value = comment
        data = comment_schema.ActivityCommentUpdate(content="new")
        result = comments_crud.update_comment(comment_id=4, user_id=7, data=data, db=mock_db)
        assert result is comment
        assert comment.content == "new"
        mock_db.commit.assert_called_once()

    def test_foreign_user_cannot_edit(self, mock_db):
        from tests._helpers.db import setup_mock_execute

        comment = SimpleNamespace(id=4, activity_id=10, user_id=7, content="old")
        setup_mock_execute(mock_db, return_scalars_all=[])
        mock_db.scalars.return_value.first.return_value = comment
        with pytest.raises(HTTPException) as exc:
            comments_crud.update_comment(
                comment_id=4,
                user_id=99,
                data=comment_schema.ActivityCommentUpdate(content="hijack"),
                db=mock_db,
            )
        assert exc.value.status_code == 403
