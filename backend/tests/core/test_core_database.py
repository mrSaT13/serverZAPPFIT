"""Tests for core.database module — get_db generator coverage."""

from unittest.mock import MagicMock, patch

import pytest

import core.database as core_database


class TestGetDb:
    """Tests for get_db generator."""

    def test_get_db_cleans_up(self):
        """get_db closes session after yield (finally block)."""
        mock_db = MagicMock()
        with patch("core.database.SessionLocal", return_value=mock_db):
            gen = core_database.get_db()
            db = next(gen)
            assert db is mock_db
            with pytest.raises(StopIteration):
                next(gen)
            mock_db.close.assert_called_once()
            mock_db.rollback.assert_not_called()

    def test_get_db_rolls_back_on_exception(self):
        """get_db rolls back and re-raises on exception (lines 118-120)."""
        mock_db = MagicMock()
        with patch("core.database.SessionLocal", return_value=mock_db):
            gen = core_database.get_db()
            db = next(gen)
            assert db is mock_db
            with pytest.raises(RuntimeError, match="db error"):
                gen.throw(RuntimeError("db error"))
            mock_db.rollback.assert_called_once()
            mock_db.close.assert_called_once()
