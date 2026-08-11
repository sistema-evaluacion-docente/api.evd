"""
Tests for EvaluationsRepository layer.
"""

from unittest.mock import MagicMock, patch

import pytest

from api.models.evaluation import EvaluationModel
from api.repositories.evaluations import EvaluationsRepository


class TestEvaluationsRepository:
    """Test suite for EvaluationsRepository."""

    @pytest.fixture
    def repo(self, mock_db):
        """Create repository instance with mocked DB."""

        return EvaluationsRepository(mock_db)

    @pytest.fixture
    def mock_evaluation_model(self):
        """Mock EvaluationModel instance."""

        evaluation = MagicMock(spec=EvaluationModel)
        evaluation.id = 1
        evaluation.department_id = 1
        return evaluation

    def test_get_by_id_as_dict_returns_none_when_not_found(self, repo, mock_db):
        """Test get_by_id_as_dict returns None when evaluation doesn't exist."""

        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = repo.get_by_id_as_dict(999)

        assert result is None

    def test_get_by_id_as_dict_includes_overall_average(
        self, repo, mock_db, mock_evaluation_model
    ):
        """Test get_by_id_as_dict merges the computed overall_average into the dict."""

        mock_db.query.return_value.filter.return_value.first.return_value = (
            mock_evaluation_model
        )
        mock_db.query.return_value.filter.return_value.scalar.return_value = 4.5

        with patch(
            "api.repositories.evaluations.evaluation_to_dict",
            return_value={"id": 1, "department_id": 1},
        ):
            result = repo.get_by_id_as_dict(1)

        assert result["id"] == 1
        assert result["overall_average"] == 4.5

    def test_get_overall_average_returns_none_when_no_scores(self, repo, mock_db):
        """Test _get_overall_average returns None when there are no scores yet."""

        mock_db.query.return_value.filter.return_value.scalar.return_value = None

        result = repo._get_overall_average(1)

        assert result is None

    def test_get_overall_average_returns_float(self, repo, mock_db):
        """Test _get_overall_average casts the DB average to float."""

        mock_db.query.return_value.filter.return_value.scalar.return_value = 3.75

        result = repo._get_overall_average(1)

        assert result == 3.75
        assert isinstance(result, float)

    def test_get_dimension_detail_includes_overall_when_filtered(
        self, repo, mock_db, mock_evaluation_model
    ):
        """Test get_dimension_detail nests an unfiltered 'overall' breakdown
        when narrowed by teacher_id/course_id, so it can be compared against."""

        mock_evaluation_model.academic_period = MagicMock(code="2024-1", name="2024-1")

        query_mock = mock_db.query.return_value
        # 1 filter (evaluation_id only) — the recursive unfiltered call
        query_mock.join.return_value.filter.return_value.all.return_value = []
        # 2 filters (evaluation_id + teacher_id) — the outer filtered call
        query_mock.join.return_value.filter.return_value.filter.return_value.all.return_value = (
            []
        )
        query_mock.filter.return_value.scalar.return_value = None

        with patch.object(repo, "get_by_id", return_value=mock_evaluation_model):
            result = repo.get_dimension_detail(1, teacher_id=7)

        assert result is not None
        assert result["overall"] is not None
        assert "overall" not in result["overall"]

    def test_get_dimension_detail_omits_overall_when_unfiltered(
        self, repo, mock_db, mock_evaluation_model
    ):
        """Test get_dimension_detail has no 'overall' key without a filter."""

        mock_evaluation_model.academic_period = MagicMock(code="2024-1", name="2024-1")

        query_mock = mock_db.query.return_value
        query_mock.join.return_value.filter.return_value.all.return_value = []
        query_mock.filter.return_value.scalar.return_value = None

        with patch.object(repo, "get_by_id", return_value=mock_evaluation_model):
            result = repo.get_dimension_detail(1)

        assert result is not None
        assert "overall" not in result
