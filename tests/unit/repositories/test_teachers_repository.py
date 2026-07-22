"""
Tests for TeachersRepository layer.
"""

from unittest.mock import MagicMock

import pytest

from api.core.pagination import PaginationParams
from api.models.teacher import TeacherModel
from api.repositories.base import BaseRepository
from api.repositories.teachers import TeachersRepository
from api.schemas.teacher import TeacherFilters


class TestTeachersRepository:
    """Test suite for TeachersRepository."""

    @pytest.fixture
    def repo(self, mock_db):
        """Create repository instance with mocked DB."""

        return TeachersRepository(mock_db)

    @pytest.fixture
    def mock_teacher_model(self):
        """Mock TeacherModel instance."""

        teacher = MagicMock(spec=TeacherModel)
        teacher.id = 1
        teacher.department_id = 1
        teacher.contract_type = "FULL_TIME"
        teacher.user_id = 1
        teacher.active = True
        teacher.user = MagicMock()
        teacher.user.institutional_code = "12345"
        return teacher

    def test_inherits_base_repository(self, repo):
        """Test TeachersRepository inherits from BaseRepository."""

        assert isinstance(repo, BaseRepository)

    def test_get_by_id_found(self, repo, mock_db, mock_teacher_model):
        """Test get_by_id returns teacher when found."""

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.options.return_value = mock_query
        mock_query.filter.return_value.first.return_value = mock_teacher_model

        result = repo.get_by_id(1)

        assert result == mock_teacher_model
        mock_db.query.assert_called_once_with(TeacherModel)

    def test_get_by_id_not_found(self, repo, mock_db):
        """Test get_by_id returns None when teacher not found."""

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.options.return_value = mock_query
        mock_query.filter.return_value.first.return_value = None

        result = repo.get_by_id(999)

        assert result is None

    def test_get_by_institutional_code_found(self, repo, mock_db, mock_teacher_model):
        """Test get_by_institutional_code returns teacher when found."""

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.join.return_value = mock_query
        mock_query.filter.return_value.first.return_value = mock_teacher_model

        result = repo.get_by_institutional_code("12345")

        assert result == mock_teacher_model

    def test_get_by_institutional_code_not_found(self, repo, mock_db):
        """Test get_by_institutional_code returns None when not found."""

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.join.return_value = mock_query
        mock_query.filter.return_value.first.return_value = None

        result = repo.get_by_institutional_code("99999")

        assert result is None

    def test_get_by_institutional_codes_empty(self, repo, mock_db):
        """Test get_by_institutional_codes returns empty list for empty input."""

        result = repo.get_by_institutional_codes([])

        assert result == []

    def test_get_by_institutional_codes(self, repo, mock_db, mock_teacher_model):
        """Test get_by_institutional_codes returns matching teachers."""

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.join.return_value = mock_query
        mock_query.filter.return_value.all.return_value = [mock_teacher_model]

        result = repo.get_by_institutional_codes(["12345"])

        assert len(result) == 1
        assert result[0] == mock_teacher_model

    def test_search_no_filters(self, repo, mock_db, mock_teacher_model):
        """Test search with no filters returns all teachers paginated."""

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.options.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.offset.return_value.limit.return_value.all.return_value = [
            mock_teacher_model
        ]

        filters = TeacherFilters()
        pagination = PaginationParams(page=1, limit=10)

        items, total = repo.search(filters, pagination)

        assert total == 1
        assert items == [mock_teacher_model]
        mock_query.count.assert_called_once()
        mock_query.offset.assert_called_once_with(0)

    def test_search_with_search_filter(self, repo, mock_db, mock_teacher_model):
        """Test search applies ilike filter for search term."""

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.options.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.offset.return_value.limit.return_value.all.return_value = [
            mock_teacher_model
        ]

        filters = TeacherFilters(search="12345")
        pagination = PaginationParams(page=1, limit=10)

        items, total = repo.search(filters, pagination)

        assert total == 1
        mock_query.filter.assert_called_once()

    def test_search_with_active_filter(self, repo, mock_db, mock_teacher_model):
        """Test search applies equality filter for active status."""

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.options.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.offset.return_value.limit.return_value.all.return_value = [
            mock_teacher_model
        ]

        filters = TeacherFilters(active=True)
        pagination = PaginationParams(page=1, limit=10)

        items, total = repo.search(filters, pagination)

        assert total == 1

    def test_search_with_department_filter(self, repo, mock_db, mock_teacher_model):
        """Test search applies filter for department_id."""

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.options.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.offset.return_value.limit.return_value.all.return_value = [
            mock_teacher_model
        ]

        filters = TeacherFilters(department_id=1)
        pagination = PaginationParams(page=1, limit=10)

        items, total = repo.search(filters, pagination)

        assert total == 1

    def test_search_with_contract_type_filter(self, repo, mock_db, mock_teacher_model):
        """Test search applies filter for contract_type."""

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.options.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.offset.return_value.limit.return_value.all.return_value = [
            mock_teacher_model
        ]

        filters = TeacherFilters(contract_type="FULL_TIME")
        pagination = PaginationParams(page=1, limit=10)

        items, total = repo.search(filters, pagination)

        assert total == 1

    def test_search_pagination_offset(self, repo, mock_db, mock_teacher_model):
        """Test search calculates correct offset for page > 1."""

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.options.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.count.return_value = 25
        mock_query.offset.return_value.limit.return_value.all.return_value = [
            mock_teacher_model
        ]

        filters = TeacherFilters()
        pagination = PaginationParams(page=3, limit=10)

        items, total = repo.search(filters, pagination)

        assert total == 25
        mock_query.offset.assert_called_once_with(20)

    def test_update_teacher(self, repo, mock_db, mock_teacher_model):
        """Test update_teacher updates teacher attributes."""

        result = repo.update_teacher(mock_teacher_model, {"contract_type": "PART_TIME"})

        assert mock_teacher_model.contract_type == "PART_TIME"
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once_with(mock_teacher_model)
        assert result == mock_teacher_model

    def test_delete_teacher_success(self, repo, mock_db, mock_teacher_model):
        """Test delete_teacher deletes and returns teacher."""

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.options.return_value = mock_query
        mock_query.filter.return_value.first.return_value = mock_teacher_model

        result = repo.delete_teacher(1)

        assert result == mock_teacher_model
        mock_db.delete.assert_called_once_with(mock_teacher_model)
        mock_db.commit.assert_called_once()

    def test_delete_teacher_not_found(self, repo, mock_db):
        """Test delete_teacher returns None when not found."""

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.options.return_value = mock_query
        mock_query.filter.return_value.first.return_value = None

        result = repo.delete_teacher(999)

        assert result is None

    def test_get_teacher_averages_by_period_empty(self, repo, mock_db):
        """Test get_teacher_averages_by_period returns empty dict for empty input."""

        result = repo.get_teacher_averages_by_period([], 1)

        assert result == {}

    def test_get_teacher_averages_by_period(self, repo, mock_db):
        """Test get_teacher_averages_by_period returns averages dict."""

        mock_row = MagicMock()
        mock_row.teacher_id = 1
        mock_row.avg = 4.5

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.join.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.group_by.return_value = mock_query
        mock_query.all.return_value = [mock_row]

        result = repo.get_teacher_averages_by_period([1], 1)

        assert result == {1: 4.5}
