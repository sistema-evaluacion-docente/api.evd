"""Tests for CoursesRepository layer."""

from unittest.mock import MagicMock

import pytest

from api.core.pagination import PaginationParams
from api.models.course import CourseModel
from api.repositories.courses import CoursesRepository
from api.repositories.base import BaseRepository
from api.schemas.course import CourseFilters


class TestCoursesRepository:
    """Test suite for CoursesRepository."""

    @pytest.fixture
    def repo(self, mock_db):
        """Create repository instance with mocked DB."""

        return CoursesRepository(mock_db)

    @pytest.fixture
    def mock_course_model(self):
        """Mock CourseModel instance."""

        course = MagicMock(spec=CourseModel)
        course.id = 1
        course.code = "MATH101"
        course.name = "Cálculo I"
        course.department_id = 5
        return course

    @pytest.fixture
    def mock_query(self, mock_db):
        """Mock a chained SQLAlchemy query."""

        query = MagicMock()
        mock_db.query.return_value = query
        query.options.return_value = query
        query.filter.return_value = query
        query.order_by.return_value = query
        return query

    def test_inherits_base_repository(self, repo):
        """Test CoursesRepository inherits from BaseRepository."""

        assert isinstance(repo, BaseRepository)

    def test_get_by_id_found(self, repo, mock_db, mock_course_model):
        """Test get_by_id returns course when found."""

        mock_db.query.return_value.options.return_value.filter.return_value.first.return_value = (
            mock_course_model
        )

        result = repo.get_by_id(1)

        assert result == mock_course_model

    def test_get_by_id_not_found(self, repo, mock_db):
        """Test get_by_id returns None when not found."""

        mock_db.query.return_value.options.return_value.filter.return_value.first.return_value = (
            None
        )

        result = repo.get_by_id(999)

        assert result is None

    def test_get_by_id_eager_loads_department(self, repo, mock_db, mock_query):
        """Test get_by_id applies joinedload options to avoid N+1 queries."""

        mock_query.filter.return_value.first.return_value = None

        repo.get_by_id(1)

        mock_query.options.assert_called_once()

    def test_get_by_code_found(self, repo, mock_db, mock_course_model):
        """Test get_by_code returns course when found."""

        mock_db.query.return_value.options.return_value.filter.return_value.first.return_value = (
            mock_course_model
        )

        result = repo.get_by_code("MATH101")

        assert result == mock_course_model

    def test_get_by_code_not_found(self, repo, mock_db):
        """Test get_by_code returns None when not found."""

        mock_db.query.return_value.options.return_value.filter.return_value.first.return_value = (
            None
        )

        result = repo.get_by_code("NONEXISTENT")

        assert result is None

    def test_search_no_filters(self, repo, mock_db, mock_query, mock_course_model):
        """Test search with no filters returns all courses paginated."""

        mock_query.count.return_value = 1
        mock_query.offset.return_value.limit.return_value.all.return_value = [
            mock_course_model
        ]

        filters = CourseFilters()
        pagination = PaginationParams(page=1, limit=10)

        items, total = repo.search(filters, pagination)

        assert total == 1
        assert items == [mock_course_model]
        mock_query.count.assert_called_once()
        mock_query.offset.assert_called_once_with(0)

    def test_search_with_search_filter(
        self, repo, mock_db, mock_query, mock_course_model
    ):
        """Test search applies ilike filter for search term on code and name."""

        mock_query.count.return_value = 1
        mock_query.offset.return_value.limit.return_value.all.return_value = [
            mock_course_model
        ]

        filters = CourseFilters(search="MATH")
        pagination = PaginationParams(page=1, limit=10)

        items, total = repo.search(filters, pagination)

        assert total == 1
        mock_query.filter.assert_called()

    def test_search_with_blank_search_ignores_filter(
        self, repo, mock_db, mock_query, mock_course_model
    ):
        """Test search ignores blank search terms."""

        mock_query.count.return_value = 1
        mock_query.offset.return_value.limit.return_value.all.return_value = [
            mock_course_model
        ]

        filters = CourseFilters(search="   ")
        pagination = PaginationParams(page=1, limit=10)

        repo.search(filters, pagination)

        mock_query.filter.assert_not_called()

    def test_search_with_department_filter(
        self, repo, mock_db, mock_query, mock_course_model
    ):
        """Test search applies equality filter for department_id."""

        mock_query.count.return_value = 1
        mock_query.offset.return_value.limit.return_value.all.return_value = [
            mock_course_model
        ]

        filters = CourseFilters(department_id=5)
        pagination = PaginationParams(page=1, limit=10)

        items, total = repo.search(filters, pagination)

        assert total == 1
        mock_query.filter.assert_called_once()

    def test_search_pagination_offset(
        self, repo, mock_db, mock_query, mock_course_model
    ):
        """Test search calculates correct offset for page > 1."""

        mock_query.count.return_value = 25
        mock_query.offset.return_value.limit.return_value.all.return_value = [
            mock_course_model
        ]

        filters = CourseFilters()
        pagination = PaginationParams(page=3, limit=10)

        items, total = repo.search(filters, pagination)

        assert total == 25
        mock_query.offset.assert_called_once_with(20)

    def test_count_academic_groups(self, repo, mock_db):
        """Test count_academic_groups returns the count."""

        mock_db.query.return_value.filter.return_value.count.return_value = 3

        result = repo.count_academic_groups(1)

        assert result == 3

    def test_update_course(self, repo, mock_db, mock_course_model):
        """Test update_course updates attributes."""

        result = repo.update_course(mock_course_model, {"name": "Cálculo II"})

        assert mock_course_model.name == "Cálculo II"
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once_with(mock_course_model)
        assert result == mock_course_model

    def test_update_course_skips_none_values(self, repo, mock_db, mock_course_model):
        """Test update_course does not overwrite fields with None."""

        repo.update_course(mock_course_model, {"name": None, "code": "MATH102"})

        assert mock_course_model.name == "Cálculo I"
        assert mock_course_model.code == "MATH102"

    def test_delete_course_success(self, repo, mock_db, mock_course_model):
        """Test delete_course deletes and returns course."""

        mock_db.query.return_value.filter.return_value.first.return_value = (
            mock_course_model
        )

        result = repo.delete_course(1)

        assert result == mock_course_model
        mock_db.delete.assert_called_once_with(mock_course_model)
        mock_db.commit.assert_called_once()

    def test_delete_course_not_found(self, repo, mock_db):
        """Test delete_course returns None when not found."""

        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = repo.delete_course(999)

        assert result is None
