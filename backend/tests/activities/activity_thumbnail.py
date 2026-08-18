from unittest.mock import MagicMock, patch


class TestGenerateActivityThumbnail:
    @patch("activities.activity.thumbnail.staticmap.StaticMap")
    @patch("activities.activity.thumbnail.Path")
    def test_generate_thumbnail_success(self, mock_path, mock_staticmap, tmp_path):
        import activities.activity.thumbnail as mod

        mock_map = MagicMock()
        mock_staticmap.return_value = mock_map

        waypoints = [(38.0, -9.0), (38.5, -9.5)]

        result = mod.generate_activity_thumbnail(
            activity_id=1,
            waypoints=waypoints,
            thumbnails_dir=str(tmp_path),
        )

        assert result is not None
        mock_map.render.assert_called_once()

    @patch("activities.activity.thumbnail.staticmap.StaticMap")
    @patch("activities.activity.thumbnail.Path")
    def test_generate_thumbnail_empty_waypoints(self, mock_path, mock_staticmap, tmp_path):
        import activities.activity.thumbnail as mod

        result = mod.generate_activity_thumbnail(
            activity_id=1,
            waypoints=[],
            thumbnails_dir=str(tmp_path),
        )

        assert result is None


class TestCleanupThumbnails:
    @patch("activities.activity.thumbnail.Path")
    @patch("activities.activity.thumbnail.shutil.rmtree")
    def test_cleanup_thumbnails(self, mock_rmtree, mock_path, tmp_path):
        import activities.activity.thumbnail as mod

        mock_dir = MagicMock()
        mock_dir.iterdir.return_value = []
        mock_path.return_value = mock_dir

        mod.cleanup_thumbnails(str(tmp_path))

        mock_rmtree.assert_not_called()
