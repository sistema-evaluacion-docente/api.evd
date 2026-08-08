"""
Tests for CommentsRepository layer.
"""

from unittest.mock import MagicMock

import pytest

from api.models.comment import CommentModel
from api.repositories.comments import CommentsRepository


class TestCommentsRepository:
    """Test suite for CommentsRepository."""

    @pytest.fixture
    def repo(self, mock_db):
        """Create repository instance with mocked DB."""

        return CommentsRepository(mock_db)

    @pytest.fixture
    def mock_comment_model(self):
        """Mock CommentModel instance."""

        comment = MagicMock(spec=CommentModel)
        comment.id = 1
        comment.risk_level = 1
        comment.pedagogical_category_id = 1
        comment.risk_score = 0.42
        comment.category_score = 0.55
        comment.risk_level_modified_by_director = False
        comment.pedagogical_category_modified_by_director = False
        return comment

    def test_get_department_id_returns_id_when_found(self, repo, mock_db):
        """Test get_department_id returns the department_id of the linked evaluation."""

        mock_db.query.return_value.join.return_value.filter.return_value.first.return_value = (
            5,
        )

        result = repo.get_department_id(1)

        assert result == 5

    def test_get_department_id_returns_none_when_not_found(self, repo, mock_db):
        """Test get_department_id returns None when there is no linked evaluation."""

        mock_db.query.return_value.join.return_value.filter.return_value.first.return_value = (
            None
        )

        result = repo.get_department_id(999)

        assert result is None

    def test_update_classification_returns_none_when_comment_not_found(
        self, repo, mock_db
    ):
        """Test update_classification returns None when the comment doesn't exist."""

        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = repo.update_classification(999, risk_level=2)

        assert result is None
        mock_db.commit.assert_not_called()

    def test_update_classification_updates_risk_level_and_flags_it(
        self, repo, mock_db, mock_comment_model
    ):
        """Test update_classification updates risk_level and flags it as director-modified."""

        mock_db.query.return_value.filter.return_value.first.return_value = (
            mock_comment_model
        )

        result = repo.update_classification(1, risk_level=3)

        assert result.risk_level == 3
        assert result.risk_level_modified_by_director is True
        assert result.pedagogical_category_modified_by_director is False
        assert result.risk_score == 1
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once_with(mock_comment_model)

    def test_update_classification_updates_category_and_flags_it(
        self, repo, mock_db, mock_comment_model
    ):
        """Test update_classification updates the category and flags it as director-modified."""

        mock_db.query.return_value.filter.return_value.first.return_value = (
            mock_comment_model
        )

        result = repo.update_classification(1, pedagogical_category_id=4)

        assert result.pedagogical_category_id == 4
        assert result.pedagogical_category_modified_by_director is True
        assert result.risk_level_modified_by_director is False
        assert result.category_score == 1
        mock_db.commit.assert_called_once()

    def test_update_classification_updates_both_fields(
        self, repo, mock_db, mock_comment_model
    ):
        """Test update_classification can update both fields in one call."""

        mock_db.query.return_value.filter.return_value.first.return_value = (
            mock_comment_model
        )

        result = repo.update_classification(1, risk_level=3, pedagogical_category_id=4)

        assert result.risk_level == 3
        assert result.pedagogical_category_id == 4
        assert result.risk_level_modified_by_director is True
        assert result.pedagogical_category_modified_by_director is True
        assert result.risk_score == 1
        assert result.category_score == 1

    def test_update_classification_does_not_flag_unchanged_risk_level(
        self, repo, mock_db, mock_comment_model
    ):
        """Test update_classification skips the flag/score when risk_level is unchanged."""

        mock_db.query.return_value.filter.return_value.first.return_value = (
            mock_comment_model
        )

        result = repo.update_classification(1, risk_level=mock_comment_model.risk_level)

        assert result.risk_level_modified_by_director is False
        assert result.risk_score == 0.42
        mock_db.commit.assert_called_once()

    def test_update_classification_does_not_flag_unchanged_category(
        self, repo, mock_db, mock_comment_model
    ):
        """Test update_classification skips the flag/score when the category is unchanged."""

        mock_db.query.return_value.filter.return_value.first.return_value = (
            mock_comment_model
        )

        result = repo.update_classification(
            1, pedagogical_category_id=mock_comment_model.pedagogical_category_id
        )

        assert result.pedagogical_category_modified_by_director is False
        assert result.category_score == 0.55
        mock_db.commit.assert_called_once()
