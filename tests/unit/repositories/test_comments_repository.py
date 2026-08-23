"""
Tests for CommentsRepository layer.
"""

from unittest.mock import MagicMock

import pytest

from api.core.pagination import PaginationParams
from api.models.comment import CommentModel
from api.repositories.comments import CommentsRepository
from api.schemas.comment import CommentFilters


class TestCommentsRepository:
    """Test suite for CommentsRepository."""

    @pytest.fixture
    def repo(self, mock_db):
        """Create repository instance with mocked DB."""

        return CommentsRepository(mock_db)

    @pytest.fixture
    def mock_comment_model(self):
        """Mock CommentModel instance with one existing pedagogical category (id=1)."""

        comment = MagicMock(spec=CommentModel)
        comment.id = 1
        comment.risk_level = 1
        comment.risk_score = 0.42
        comment.risk_level_modified_by_director = False
        comment.pedagogical_category_modified_by_director = False
        comment.risk_level_ai_model = "org/risk-model-v1"
        comment.pedagogical_category_ai_model = "org/category-model-v1"

        existing_link = MagicMock()
        existing_link.pedagogical_category_id = 1
        comment.pedagogical_categories = [existing_link]
        return comment

    @pytest.fixture
    def mock_search_query(self, mock_db):
        """Mock the chained query search() builds."""

        query = MagicMock()
        mock_db.query.return_value = query
        query.outerjoin.return_value = query
        query.join.return_value = query
        query.filter.return_value = query
        query.order_by.return_value = query
        query.count.return_value = 0
        query.offset.return_value.limit.return_value.all.return_value = []
        return query

    def test_search_filters_by_modality(self, repo, mock_search_query):
        """Test search narrows the comments down to one kind of program."""

        repo.search(
            CommentFilters(modality="DISTANCIA"), PaginationParams(page=1, limit=10)
        )

        applied = [
            str(call.args[0]) for call in mock_search_query.filter.call_args_list
        ]

        assert applied == ["academic_groups.modality = :modality_1"]

    def test_search_without_modality_takes_every_group(self, repo, mock_search_query):
        """Test the comments of both kinds of program come back by default."""

        repo.search(CommentFilters(), PaginationParams(page=1, limit=10))

        mock_search_query.filter.assert_not_called()

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

    def test_get_teacher_user_id_returns_id_when_found(self, repo, mock_db):
        """Test get_teacher_user_id returns the user_id of the comment's teacher."""

        mock_db.query.return_value.join.return_value.filter.return_value.first.return_value = (
            42,
        )

        result = repo.get_teacher_user_id(1)

        assert result == 42

    def test_get_teacher_user_id_returns_none_when_not_found(self, repo, mock_db):
        """Test get_teacher_user_id returns None when there is no linked teacher."""

        mock_db.query.return_value.join.return_value.filter.return_value.first.return_value = (
            None
        )

        result = repo.get_teacher_user_id(999)

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
        assert result.risk_level_ai_model is None
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once_with(mock_comment_model)

    def test_update_classification_updates_category_and_flags_it(
        self, repo, mock_db, mock_comment_model
    ):
        """Test update_classification replaces the categories and flags it as director-modified."""

        mock_db.query.return_value.filter.return_value.first.return_value = (
            mock_comment_model
        )

        result = repo.update_classification(1, pedagogical_category_ids=[4])

        assert [
            link.pedagogical_category_id for link in result.pedagogical_categories
        ] == [4]
        assert [link.score for link in result.pedagogical_categories] == [1]
        assert result.pedagogical_category_modified_by_director is True
        assert result.risk_level_modified_by_director is False
        assert result.pedagogical_category_ai_model is None
        mock_db.commit.assert_called_once()

    def test_update_classification_supports_multiple_categories(
        self, repo, mock_db, mock_comment_model
    ):
        """Test update_classification can assign several categories at once."""

        mock_db.query.return_value.filter.return_value.first.return_value = (
            mock_comment_model
        )

        result = repo.update_classification(1, pedagogical_category_ids=[2, 4])

        assert sorted(
            link.pedagogical_category_id for link in result.pedagogical_categories
        ) == [2, 4]
        assert result.pedagogical_category_modified_by_director is True

    def test_update_classification_supports_zero_categories(
        self, repo, mock_db, mock_comment_model
    ):
        """Test update_classification can clear all categories with an empty list."""

        mock_db.query.return_value.filter.return_value.first.return_value = (
            mock_comment_model
        )

        result = repo.update_classification(1, pedagogical_category_ids=[])

        assert result.pedagogical_categories == []
        assert result.pedagogical_category_modified_by_director is True

    def test_update_classification_updates_both_fields(
        self, repo, mock_db, mock_comment_model
    ):
        """Test update_classification can update both fields in one call."""

        mock_db.query.return_value.filter.return_value.first.return_value = (
            mock_comment_model
        )

        result = repo.update_classification(
            1, risk_level=3, pedagogical_category_ids=[4]
        )

        assert result.risk_level == 3
        assert [
            link.pedagogical_category_id for link in result.pedagogical_categories
        ] == [4]
        assert result.risk_level_modified_by_director is True
        assert result.pedagogical_category_modified_by_director is True
        assert result.risk_score == 1

    def test_update_classification_clears_only_the_overridden_half_of_the_attribution(
        self, repo, mock_db, mock_comment_model
    ):
        """Test overriding the risk level leaves the category model attribution intact."""

        mock_db.query.return_value.filter.return_value.first.return_value = (
            mock_comment_model
        )

        result = repo.update_classification(1, risk_level=3)

        assert result.risk_level_ai_model is None
        assert result.pedagogical_category_ai_model == "org/category-model-v1"

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
        assert result.risk_level_ai_model == "org/risk-model-v1"
        mock_db.commit.assert_called_once()

    def test_update_classification_does_not_flag_unchanged_category(
        self, repo, mock_db, mock_comment_model
    ):
        """Test update_classification skips the flag when the category set is unchanged."""

        mock_db.query.return_value.filter.return_value.first.return_value = (
            mock_comment_model
        )
        existing_ids = [
            link.pedagogical_category_id
            for link in mock_comment_model.pedagogical_categories
        ]

        result = repo.update_classification(1, pedagogical_category_ids=existing_ids)

        assert result.pedagogical_category_modified_by_director is False
        assert result.pedagogical_category_ai_model == "org/category-model-v1"
        mock_db.commit.assert_called_once()
