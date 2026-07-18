"""
Tests for FacultiesRepository layer.
"""

from unittest.mock import MagicMock

import pytest

from api.core.pagination import PaginationParams
from api.models.faculty import FacultyModel
from api.repositories.base import BaseRepository
from api.repositories.faculties import FacultiesRepository
from api.schemas.faculty import FacultyFilters


class TestFacultiesRepository:
    """Test suite for FacultiesRepository."""

    @pytest.fixture
    def repo(self, mock_db):
        """Create repository instance with mocked DB."""

        return FacultiesRepository(mock_db)

    @pytest.fixture
    def mock_faculty_model(self):
        """Mock FacultyModel instance."""

        faculty = MagicMock(spec=FacultyModel)
        faculty.id = 1
        faculty.name = "Engineering"
        faculty.code = "ENG"
        faculty.active = True
        return faculty

    def test_inherits_base_repository(self, repo):
        """Test FacultiesRepository inherits from BaseRepository."""

        assert isinstance(repo, BaseRepository)

    def test_get_by_code_found(self, repo, mock_db, mock_faculty_model):
        """Test get_by_code returns faculty when found."""

        mock_db.query.return_value.filter.return_value.first.return_value = (
            mock_faculty_model
        )

        result = repo.get_by_code("ENG")

        assert result == mock_faculty_model

    def test_get_by_code_not_found(self, repo, mock_db):
        """Test get_by_code returns None when not found."""

        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = repo.get_by_code("NONEXISTENT")

        assert result is None

    def test_search_no_filters(self, repo, mock_db, mock_faculty_model):
        """Test search with no filters returns all faculties paginated."""

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.offset.return_value.limit.return_value.all.return_value = [
            mock_faculty_model
        ]

        filters = FacultyFilters()
        pagination = PaginationParams(page=1, limit=10)

        items, total = repo.search(filters, pagination)

        assert total == 1
        assert items == [mock_faculty_model]
        mock_query.count.assert_called_once()
        mock_query.offset.assert_called_once_with(0)

    def test_search_with_search_filter(self, repo, mock_db, mock_faculty_model):
        """Test search applies ilike filter for search term."""

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.offset.return_value.limit.return_value.all.return_value = [
            mock_faculty_model
        ]

        filters = FacultyFilters(search="Engineering")
        pagination = PaginationParams(page=1, limit=10)

        items, total = repo.search(filters, pagination)

        assert total == 1
        mock_query.filter.assert_called_once()

    def test_search_with_active_filter(self, repo, mock_db, mock_faculty_model):
        """Test search applies equality filter for active status."""

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.offset.return_value.limit.return_value.all.return_value = [
            mock_faculty_model
        ]

        filters = FacultyFilters(active=True)
        pagination = PaginationParams(page=1, limit=10)

        items, total = repo.search(filters, pagination)

        assert total == 1

    def test_search_pagination_offset(self, repo, mock_db, mock_faculty_model):
        """Test search calculates correct offset for page > 1."""

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.count.return_value = 25
        mock_query.offset.return_value.limit.return_value.all.return_value = [
            mock_faculty_model
        ]

        filters = FacultyFilters()
        pagination = PaginationParams(page=3, limit=10)

        items, total = repo.search(filters, pagination)

        assert total == 25
        mock_query.offset.assert_called_once_with(20)

    def test_has_departments_true(self, repo, mock_db):
        """Test has_departments returns True when departments exist."""

        mock_db.query.return_value.filter.return_value.count.return_value = 5

        result = repo.has_departments(1)

        assert result is True

    def test_has_departments_false(self, repo, mock_db):
        """Test has_departments returns False when no departments."""

        mock_db.query.return_value.filter.return_value.count.return_value = 0

        result = repo.has_departments(1)

        assert result is False

    def test_get_department_counts_empty(self, repo, mock_db):
        """Test get_department_counts returns empty dict for empty input."""

        result = repo.get_department_counts([])

        assert result == {}

    def test_get_department_counts(self, repo, mock_db):
        """Test get_department_counts returns counts dict."""

        mock_db.query.return_value.filter.return_value.group_by.return_value.all.return_value = [
            (1, 5),
            (2, 3),
        ]

        result = repo.get_department_counts([1, 2])

        assert result == {1: 5, 2: 3}
