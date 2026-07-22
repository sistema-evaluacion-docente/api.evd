"""
Tests for DepartmentsRepository layer.
"""

from unittest.mock import MagicMock

import pytest

from api.core.pagination import PaginationParams
from api.models.department import DepartmentModel
from api.repositories.base import BaseRepository
from api.repositories.departments import DepartmentsRepository
from api.schemas.department import DepartmentFilters


class TestDepartmentsRepository:
    """Test suite for DepartmentsRepository."""

    @pytest.fixture
    def repo(self, mock_db):
        """Create repository instance with mocked DB."""

        return DepartmentsRepository(mock_db)

    @pytest.fixture
    def mock_department_model(self):
        """Mock DepartmentModel instance."""

        dept = MagicMock(spec=DepartmentModel)
        dept.id = 1
        dept.code = "CS"
        dept.name = "Computer Science"
        dept.faculty_id = 1
        dept.active = True
        return dept

    def test_inherits_base_repository(self, repo):
        """Test DepartmentsRepository inherits from BaseRepository."""

        assert isinstance(repo, BaseRepository)

    def test_get_by_id_found(self, repo, mock_db, mock_department_model):
        """Test get_by_id returns department when found."""

        mock_db.query.return_value.filter.return_value.first.return_value = (
            mock_department_model
        )

        result = repo.get_by_id(1)

        assert result == mock_department_model

    def test_get_by_id_not_found(self, repo, mock_db):
        """Test get_by_id returns None when not found."""

        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = repo.get_by_id(999)

        assert result is None

    def test_get_by_code_found(self, repo, mock_db, mock_department_model):
        """Test get_by_code returns department when found."""

        mock_db.query.return_value.filter.return_value.first.return_value = (
            mock_department_model
        )

        result = repo.get_by_code("CS")

        assert result == mock_department_model

    def test_get_by_code_not_found(self, repo, mock_db):
        """Test get_by_code returns None when not found."""

        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = repo.get_by_code("NONEXISTENT")

        assert result is None

    def test_search_no_filters(self, repo, mock_db, mock_department_model):
        """Test search with no filters returns all departments paginated."""

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.offset.return_value.limit.return_value.all.return_value = [
            mock_department_model
        ]

        filters = DepartmentFilters()
        pagination = PaginationParams(page=1, limit=10)

        items, total = repo.search(filters, pagination)

        assert total == 1
        assert items == [mock_department_model]
        mock_query.count.assert_called_once()
        mock_query.offset.assert_called_once_with(0)

    def test_search_with_search_filter(self, repo, mock_db, mock_department_model):
        """Test search applies ilike filter for search term."""

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.offset.return_value.limit.return_value.all.return_value = [
            mock_department_model
        ]

        filters = DepartmentFilters(search="Computer")
        pagination = PaginationParams(page=1, limit=10)

        items, total = repo.search(filters, pagination)

        assert total == 1
        mock_query.filter.assert_called_once()

    def test_search_with_active_filter(self, repo, mock_db, mock_department_model):
        """Test search applies equality filter for active status."""

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.offset.return_value.limit.return_value.all.return_value = [
            mock_department_model
        ]

        filters = DepartmentFilters(active=True)
        pagination = PaginationParams(page=1, limit=10)

        items, total = repo.search(filters, pagination)

        assert total == 1

    def test_search_with_faculty_filter(self, repo, mock_db, mock_department_model):
        """Test search applies filter for faculty_id."""

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.offset.return_value.limit.return_value.all.return_value = [
            mock_department_model
        ]

        filters = DepartmentFilters(faculty_id=1)
        pagination = PaginationParams(page=1, limit=10)

        items, total = repo.search(filters, pagination)

        assert total == 1

    def test_search_pagination_offset(self, repo, mock_db, mock_department_model):
        """Test search calculates correct offset for page > 1."""

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.count.return_value = 25
        mock_query.offset.return_value.limit.return_value.all.return_value = [
            mock_department_model
        ]

        filters = DepartmentFilters()
        pagination = PaginationParams(page=3, limit=10)

        items, total = repo.search(filters, pagination)

        assert total == 25
        mock_query.offset.assert_called_once_with(20)

    def test_has_active_teachers_true(self, repo, mock_db):
        """Test has_active_teachers returns True when teachers exist."""

        mock_db.query.return_value.filter.return_value.count.return_value = 5

        result = repo.has_active_teachers(1)

        assert result is True

    def test_has_active_teachers_false(self, repo, mock_db):
        """Test has_active_teachers returns False when no teachers."""

        mock_db.query.return_value.filter.return_value.count.return_value = 0

        result = repo.has_active_teachers(1)

        assert result is False

    def test_has_active_director_true(self, repo, mock_db):
        """Test has_active_director returns True when director exists."""

        mock_db.query.return_value.filter.return_value.count.return_value = 1

        result = repo.has_active_director(1)

        assert result is True

    def test_has_active_director_false(self, repo, mock_db):
        """Test has_active_director returns False when no director."""

        mock_db.query.return_value.filter.return_value.count.return_value = 0

        result = repo.has_active_director(1)

        assert result is False

    def test_update_department(self, repo, mock_db, mock_department_model):
        """Test update_department updates attributes."""

        result = repo.update_department(mock_department_model, {"name": "New Name"})

        assert mock_department_model.name == "New Name"
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once_with(mock_department_model)
        assert result == mock_department_model

    def test_delete_department_success(self, repo, mock_db, mock_department_model):
        """Test delete_department deletes and returns department."""

        mock_db.query.return_value.filter.return_value.first.return_value = (
            mock_department_model
        )

        result = repo.delete_department(1)

        assert result == mock_department_model
        mock_db.delete.assert_called_once_with(mock_department_model)
        mock_db.commit.assert_called_once()

    def test_delete_department_not_found(self, repo, mock_db):
        """Test delete_department returns None when not found."""

        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = repo.delete_department(999)

        assert result is None

    def test_get_director_by_department_id_found(self, repo, mock_db):
        """Test get_director_by_department_id returns director info."""

        mock_row = MagicMock()
        mock_row.id = 10
        mock_row.name = "Director Name"
        mock_row.avatar_url = "http://example.com/avatar.png"

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.select_from.return_value = mock_query
        mock_query.join.return_value = mock_query
        mock_query.filter.return_value.first.return_value = mock_row

        result = repo.get_director_by_department_id(1)

        assert result is not None
        assert result["id"] == 10
        assert result["name"] == "Director Name"

    def test_get_director_by_department_id_not_found(self, repo, mock_db):
        """Test get_director_by_department_id returns None when no director."""

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.select_from.return_value = mock_query
        mock_query.join.return_value = mock_query
        mock_query.filter.return_value.first.return_value = None

        result = repo.get_director_by_department_id(1)

        assert result is None

    def test_get_directors_by_department_ids_empty(self, repo, mock_db):
        """Test get_directors_by_department_ids returns empty dict for empty input."""

        result = repo.get_directors_by_department_ids([])

        assert result == {}

    def test_count_teachers_by_department_ids_empty(self, repo, mock_db):
        """Test count_teachers_by_department_ids returns empty dict for empty input."""

        result = repo.count_teachers_by_department_ids([])

        assert result == {}
