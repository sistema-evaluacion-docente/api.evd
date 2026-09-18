"""
Tests for FacultiesRepository layer.
"""

from unittest.mock import MagicMock

import pytest

from api.core.pagination import PaginationParams
from api.models.dean import DeanModel
from api.models.faculty import FacultyModel
from api.repositories.base import BaseRepository
from api.repositories.faculties import FacultiesRepository
from api.schemas.faculty import FacultyCreate, FacultyFilters, FacultyUpdate


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

    def test_create_faculty(self, repo, mock_db):
        """Test create_faculty persists and returns the new faculty."""

        data = FacultyCreate(name="Ingenierías", code="ING")

        result = repo.create_faculty(data)

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        assert result.name == "Ingenierías"

    def test_update_faculty_applies_only_set_fields(
        self, repo, mock_db, mock_faculty_model
    ):
        """Test update_faculty only overwrites fields present in the payload."""

        data = FacultyUpdate(name="Ciencias")

        result = repo.update_faculty(mock_faculty_model, data)

        assert mock_faculty_model.name == "Ciencias"
        mock_db.commit.assert_called_once()
        assert result == mock_faculty_model

    def test_delete_faculty(self, repo, mock_db, mock_faculty_model):
        """Test delete_faculty deletes and commits."""

        repo.delete_faculty(mock_faculty_model)

        mock_db.delete.assert_called_once_with(mock_faculty_model)
        mock_db.commit.assert_called_once()

    @pytest.fixture
    def mock_dean_model(self):
        """Mock DeanModel instance."""

        dean = MagicMock(spec=DeanModel)
        dean.id = 1
        dean.user_id = 10
        dean.faculty_id = 1
        dean.active = True
        return dean

    def test_get_dean_by_faculty_id_found(self, repo, mock_db, mock_dean_model):
        """Test get_dean_by_faculty_id returns dean when found."""

        mock_db.query.return_value.filter.return_value.first.return_value = (
            mock_dean_model
        )

        result = repo.get_dean_by_faculty_id(1)

        assert result == mock_dean_model

    def test_get_dean_by_faculty_id_not_found(self, repo, mock_db):
        """Test get_dean_by_faculty_id returns None when not found."""

        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = repo.get_dean_by_faculty_id(999)

        assert result is None

    def test_get_dean_by_user_id_found(self, repo, mock_db, mock_dean_model):
        """Test get_dean_by_user_id returns dean when found."""

        mock_db.query.return_value.filter.return_value.first.return_value = (
            mock_dean_model
        )

        result = repo.get_dean_by_user_id(10)

        assert result == mock_dean_model

    def test_assign_dean_success(self, repo, mock_db):
        """Test assign_dean creates a new dean when none exists."""

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value.first.side_effect = [None, None]

        result = repo.assign_dean(10, 1)

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        assert result is not None

    def test_assign_dean_replaces_existing_faculty_dean(
        self, repo, mock_db, mock_dean_model
    ):
        """Test assign_dean replaces the existing dean for that faculty."""

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value.first.side_effect = [None, mock_dean_model]

        repo.assign_dean(20, 1)

        assert mock_dean_model.user_id == 20
        mock_db.commit.assert_called_once()

    def test_assign_dean_user_already_dean_of_other_faculty_raises(
        self, repo, mock_db, mock_dean_model
    ):
        """Test assign_dean raises when the user is already dean elsewhere."""

        mock_dean_model.faculty_id = 2

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value.first.return_value = mock_dean_model

        with pytest.raises(ValueError) as exc_info:
            repo.assign_dean(10, 1)

        assert "Este usuario ya es decano de otra facultad" in str(exc_info.value)

    def test_delete_dean(self, repo, mock_db, mock_dean_model):
        """Test delete_dean deletes and commits."""

        repo.delete_dean(mock_dean_model)

        mock_db.delete.assert_called_once_with(mock_dean_model)
        mock_db.commit.assert_called_once()

    def test_get_dean_with_user_by_faculty_id_found(self, repo, mock_db):
        """Test get_dean_with_user_by_faculty_id returns user info when found."""

        row = MagicMock(id=10, avatar_url=None)
        row.name = "Decano"
        mock_db.query.return_value.select_from.return_value.join.return_value.filter.return_value.first.return_value = (
            row
        )

        result = repo.get_dean_with_user_by_faculty_id(1)

        assert result == {"id": 10, "name": "Decano", "avatar_url": None}

    def test_get_dean_with_user_by_faculty_id_not_found(self, repo, mock_db):
        """Test get_dean_with_user_by_faculty_id returns None when no dean."""

        mock_db.query.return_value.select_from.return_value.join.return_value.filter.return_value.first.return_value = (
            None
        )

        result = repo.get_dean_with_user_by_faculty_id(999)

        assert result is None

    def test_get_deans_by_faculty_ids_empty_input(self, repo, mock_db):
        """Test get_deans_by_faculty_ids returns empty dict for empty input."""

        result = repo.get_deans_by_faculty_ids([])

        assert result == {}

    def test_get_deans_by_faculty_ids(self, repo, mock_db):
        """Test get_deans_by_faculty_ids returns a dict keyed by faculty_id."""

        row1 = MagicMock(id=10, avatar_url=None, faculty_id=1)
        row1.name = "Decano Uno"
        row2 = MagicMock(id=20, avatar_url=None, faculty_id=2)
        row2.name = "Decano Dos"
        mock_db.query.return_value.select_from.return_value.join.return_value.filter.return_value.all.return_value = [
            row1,
            row2,
        ]

        result = repo.get_deans_by_faculty_ids([1, 2])

        assert result == {
            1: {"id": 10, "name": "Decano Uno", "avatar_url": None},
            2: {"id": 20, "name": "Decano Dos", "avatar_url": None},
        }
