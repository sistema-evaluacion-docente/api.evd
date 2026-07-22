"""Tests for AcademicGroupsRepository layer."""

from unittest.mock import MagicMock

import pytest

from api.core.pagination import PaginationParams
from api.models.academic_group import AcademicGroupModel
from api.repositories.academic_groups import AcademicGroupsRepository
from api.repositories.base import BaseRepository
from api.schemas.academic_group import AcademicGroupFilters


class TestAcademicGroupsRepository:
    """Test suite for AcademicGroupsRepository."""

    @pytest.fixture
    def repo(self, mock_db):
        """Create repository instance with mocked DB."""

        return AcademicGroupsRepository(mock_db)

    @pytest.fixture
    def mock_group_model(self):
        """Mock AcademicGroupModel instance."""

        group = MagicMock(spec=AcademicGroupModel)
        group.id = 1
        group.course_id = 10
        group.teacher_id = 20
        group.academic_period_id = 1
        group.group_name = "A"
        return group

    @pytest.fixture
    def mock_query(self, mock_db):
        """Mock a chained SQLAlchemy query."""

        query = MagicMock()
        mock_db.query.return_value = query
        query.options.return_value = query
        query.join.return_value = query
        query.filter.return_value = query
        query.order_by.return_value = query
        return query

    def test_inherits_base_repository(self, repo):
        """Test AcademicGroupsRepository inherits from BaseRepository."""

        assert isinstance(repo, BaseRepository)

    def test_get_by_id_found(self, repo, mock_db, mock_group_model):
        """Test get_by_id returns group when found."""

        mock_db.query.return_value.options.return_value.filter.return_value.first.return_value = (
            mock_group_model
        )

        result = repo.get_by_id(1)

        assert result == mock_group_model

    def test_get_by_id_not_found(self, repo, mock_db):
        """Test get_by_id returns None when not found."""

        mock_db.query.return_value.options.return_value.filter.return_value.first.return_value = (
            None
        )

        result = repo.get_by_id(999)

        assert result is None

    def test_get_by_id_eager_loads_relationships(self, repo, mock_db, mock_query):
        """Test get_by_id applies joinedload options to avoid N+1 queries."""

        mock_query.filter.return_value.first.return_value = None

        repo.get_by_id(1)

        mock_query.options.assert_called_once()

    def test_search_no_filters(self, repo, mock_db, mock_query, mock_group_model):
        """Test search with no filters returns all groups paginated."""

        mock_query.count.return_value = 1
        mock_query.offset.return_value.limit.return_value.all.return_value = [
            mock_group_model
        ]

        filters = AcademicGroupFilters()
        pagination = PaginationParams(page=1, limit=10)

        items, total = repo.search(filters, pagination)

        assert total == 1
        assert items == [mock_group_model]
        mock_query.count.assert_called_once()
        mock_query.offset.assert_called_once_with(0)
        mock_query.join.assert_not_called()

    def test_search_with_search_filter_joins_course(
        self, repo, mock_db, mock_query, mock_group_model
    ):
        """Test search joins courses and filters when a search term is given."""

        mock_query.count.return_value = 1
        mock_query.offset.return_value.limit.return_value.all.return_value = [
            mock_group_model
        ]

        filters = AcademicGroupFilters(search="MATH")
        pagination = PaginationParams(page=1, limit=10)

        items, total = repo.search(filters, pagination)

        assert total == 1
        mock_query.join.assert_called_once()
        mock_query.filter.assert_called()

    def test_search_with_blank_search_ignores_filter(
        self, repo, mock_db, mock_query, mock_group_model
    ):
        """Test search ignores blank search terms."""

        mock_query.count.return_value = 1
        mock_query.offset.return_value.limit.return_value.all.return_value = [
            mock_group_model
        ]

        filters = AcademicGroupFilters(search="   ")
        pagination = PaginationParams(page=1, limit=10)

        repo.search(filters, pagination)

        mock_query.join.assert_not_called()

    def test_search_with_id_filters(self, repo, mock_db, mock_query, mock_group_model):
        """Test search applies equality filters for FK ids."""

        mock_query.count.return_value = 1
        mock_query.offset.return_value.limit.return_value.all.return_value = [
            mock_group_model
        ]

        filters = AcademicGroupFilters(
            course_id=10, teacher_id=20, academic_period_id=1
        )
        pagination = PaginationParams(page=1, limit=10)

        items, total = repo.search(filters, pagination)

        assert total == 1
        assert mock_query.filter.call_count == 3
        mock_query.join.assert_not_called()

    def test_search_with_department_filter_joins_course(
        self, repo, mock_db, mock_query, mock_group_model
    ):
        """Test search joins courses once when filtering by department_id."""

        mock_query.count.return_value = 1
        mock_query.offset.return_value.limit.return_value.all.return_value = [
            mock_group_model
        ]

        filters = AcademicGroupFilters(search="MATH", department_id=5)
        pagination = PaginationParams(page=1, limit=10)

        items, total = repo.search(filters, pagination)

        assert total == 1
        mock_query.join.assert_called_once()

    def test_search_pagination_offset(
        self, repo, mock_db, mock_query, mock_group_model
    ):
        """Test search calculates correct offset for page > 1."""

        mock_query.count.return_value = 25
        mock_query.offset.return_value.limit.return_value.all.return_value = [
            mock_group_model
        ]

        filters = AcademicGroupFilters()
        pagination = PaginationParams(page=3, limit=10)

        items, total = repo.search(filters, pagination)

        assert total == 25
        mock_query.offset.assert_called_once_with(20)

    def test_get_by_course_teacher_period_name_found(
        self, repo, mock_db, mock_query, mock_group_model
    ):
        """Test get_by_course_teacher_period_name returns group when found."""

        mock_query.first.return_value = mock_group_model

        result = repo.get_by_course_teacher_period_name(10, 20, 1, "A")

        assert result == mock_group_model

    def test_get_by_course_teacher_period_name_not_found(
        self, repo, mock_db, mock_query
    ):
        """Test get_by_course_teacher_period_name returns None when not found."""

        mock_query.first.return_value = None

        result = repo.get_by_course_teacher_period_name(10, 20, 1, "A")

        assert result is None

    def test_get_by_course_teacher_period_name_with_null_group_name(
        self, repo, mock_db, mock_query
    ):
        """Test get_by_course_teacher_period_name handles NULL group_name."""

        mock_query.first.return_value = None

        result = repo.get_by_course_teacher_period_name(10, 20, 1, None)

        assert result is None
        mock_query.filter.assert_called()

    def test_get_by_course_teacher_period_name_exclude_id(
        self, repo, mock_db, mock_query
    ):
        """Test get_by_course_teacher_period_name excludes the given ID."""

        mock_query.first.return_value = None

        repo.get_by_course_teacher_period_name(10, 20, 1, "A", exclude_id=1)

        assert mock_query.filter.call_count >= 2

    def test_get_by_teacher_and_period(self, repo, mock_db, mock_group_model):
        """Test get_by_teacher_and_period returns matching groups."""

        mock_db.query.return_value.options.return_value.filter.return_value.all.return_value = [
            mock_group_model
        ]

        result = repo.get_by_teacher_and_period(20, 1)

        assert result == [mock_group_model]

    def test_count_evaluation_scores(self, repo, mock_db):
        """Test count_evaluation_scores returns the count."""

        mock_db.query.return_value.filter.return_value.count.return_value = 3

        result = repo.count_evaluation_scores(1)

        assert result == 3

    def test_count_comments(self, repo, mock_db):
        """Test count_comments returns the count."""

        mock_db.query.return_value.filter.return_value.count.return_value = 2

        result = repo.count_comments(1)

        assert result == 2

    def test_update_group(self, repo, mock_db, mock_group_model):
        """Test update_group updates attributes."""

        result = repo.update_group(mock_group_model, {"group_name": "B"})

        assert mock_group_model.group_name == "B"
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once_with(mock_group_model)
        assert result == mock_group_model

    def test_update_group_skips_none_values(self, repo, mock_db, mock_group_model):
        """Test update_group does not overwrite fields with None."""

        repo.update_group(mock_group_model, {"group_name": None, "teacher_id": 30})

        assert mock_group_model.group_name == "A"
        assert mock_group_model.teacher_id == 30

    def test_delete_group_success(self, repo, mock_db, mock_group_model):
        """Test delete_group deletes and returns group."""

        mock_db.query.return_value.filter.return_value.first.return_value = (
            mock_group_model
        )

        result = repo.delete_group(1)

        assert result == mock_group_model
        mock_db.delete.assert_called_once_with(mock_group_model)
        mock_db.commit.assert_called_once()

    def test_delete_group_not_found(self, repo, mock_db):
        """Test delete_group returns None when not found."""

        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = repo.delete_group(999)

        assert result is None
