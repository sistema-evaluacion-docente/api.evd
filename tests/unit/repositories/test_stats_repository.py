"""
Tests for StatsRepository layer.
"""

from api.repositories.stats import StatsRepository


class TestStatsRepository:
    """Test suite for StatsRepository."""

    def test_get_department_comment_risk_counts_defaults_missing_levels_to_zero(
        self, mock_db
    ):
        """Test _get_department_comment_risk_counts fills in BAJO/MEDIO/ALTO
        with 0 when the department has no comments for that risk level."""

        repo = StatsRepository(mock_db)
        mock_db.query.return_value.join.return_value.join.return_value.filter.return_value.group_by.return_value.all.return_value = [
            ("ALTO", 3),
        ]

        result = repo._get_department_comment_risk_counts(1, [10, 11])

        assert result == {"BAJO": 0, "MEDIO": 0, "ALTO": 3}

    def test_get_department_comment_pedagogical_category_counts_returns_only_present_categories(
        self, mock_db
    ):
        """Test _get_department_comment_pedagogical_category_counts returns
        counts keyed by category name, without forcing a fixed catalogue
        (categories are DB-driven, unlike the fixed risk levels)."""

        repo = StatsRepository(mock_db)
        mock_db.query.return_value.join.return_value.join.return_value.join.return_value.filter.return_value.group_by.return_value.all.return_value = [
            ("LABEL_0", 5),
            ("LABEL_1", 2),
        ]

        result = repo._get_department_comment_pedagogical_category_counts(1, [10, 11])

        assert result == {"LABEL_0": 5, "LABEL_1": 2}
