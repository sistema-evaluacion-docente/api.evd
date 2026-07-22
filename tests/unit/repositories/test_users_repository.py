"""
Tests for UsersRepository layer.
"""

from unittest.mock import MagicMock
import pytest

from api.core.pagination import PaginationParams
from api.models.user import UserModel
from api.models.user_role import UserRoleModel
from api.models.teacher import TeacherModel
from api.repositories.users import UsersRepository
from api.repositories.base import BaseRepository
from api.schemas.user import UserFilters


class TestUsersRepository:
    """Test suite for UsersRepository."""

    @pytest.fixture
    def repo(self, mock_db):
        """Create repository instance with mocked DB."""

        return UsersRepository(mock_db)

    def test_get_by_uid_found(self, repo, mock_db, mock_user_model):
        """Test get_by_uid returns user when found."""

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.options.return_value = mock_query
        mock_query.filter.return_value.first.return_value = mock_user_model

        result = repo.get_by_uid("test-uid-123")

        assert result == mock_user_model
        mock_db.query.assert_called_once_with(UserModel)

    def test_get_by_uid_not_found(self, repo, mock_db):
        """Test get_by_uid returns None when user not found."""

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.options.return_value = mock_query
        mock_query.filter.return_value.first.return_value = None

        result = repo.get_by_uid("nonexistent-uid")

        assert result is None

    def test_get_by_email_found(self, repo, mock_db, mock_user_model):
        """Test get_by_email returns user when found."""

        mock_db.query.return_value.filter.return_value.first.return_value = (
            mock_user_model
        )

        result = repo.get_by_email("test@example.com")

        assert result == mock_user_model

    def test_get_by_email_not_found(self, repo, mock_db):
        """Test get_by_email returns None when user not found."""

        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = repo.get_by_email("nonexistent@example.com")

        assert result is None

    def test_get_user_role_names(self, repo, mock_db):
        """Test get_user_role_names returns list of role names."""

        mock_db.query.return_value.join.return_value.filter.return_value.all.return_value = [
            ("DOCENTE",),
            ("ADMIN",),
        ]

        result = repo.get_user_role_names(1)

        assert result == ["DOCENTE", "ADMIN"]

    def test_get_user_role_names_empty(self, repo, mock_db):
        """Test get_user_role_names returns empty list when no roles."""

        mock_db.query.return_value.join.return_value.filter.return_value.all.return_value = (
            []
        )

        result = repo.get_user_role_names(1)

        assert result == []

    def test_get_roles_by_names(self, repo, mock_db, mock_role_model):
        """Test get_roles_by_names returns role models."""

        mock_db.query.return_value.filter.return_value.all.return_value = [
            mock_role_model
        ]

        result = repo.get_roles_by_names(["DOCENTE"])

        assert len(result) == 1
        assert result[0] == mock_role_model

    def test_get_roles_by_names_empty(self, repo, mock_db):
        """Test get_roles_by_names returns empty list for empty input."""

        result = repo.get_roles_by_names([])

        assert result == []

    def test_replace_user_roles(self, repo, mock_db):
        """Test replace_user_roles deletes old and adds new roles."""

        repo.replace_user_roles(1, [1, 2])

        mock_db.query.assert_called_once_with(UserRoleModel)
        assert mock_db.add.call_count == 2

    def test_update_fields(self, repo, mock_db, mock_user_model):
        """Test update_fields updates user attributes."""

        repo.update_fields(mock_user_model, {"name": "New Name", "active": False})

        assert mock_user_model.name == "New Name"
        assert mock_user_model.active is False

        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once_with(mock_user_model)

    def test_update_fields_skips_none_values(self, repo, mock_db, mock_user_model):
        """Test update_fields skips None values."""

        original_name = mock_user_model.name
        repo.update_fields(mock_user_model, {"name": None, "active": True})

        assert mock_user_model.name == original_name
        assert mock_user_model.active is True

    def test_update_active(self, repo, mock_db, mock_user_model):
        """Test update_active updates active status."""

        repo.update_active(mock_user_model, False)

        assert mock_user_model.active is False
        mock_db.commit.assert_called_once()

    def test_get_teacher_by_user_id_found(self, repo, mock_db):
        """Test get_teacher_by_user_id returns teacher when found."""

        teacher = MagicMock(spec=TeacherModel)
        mock_db.query.return_value.filter.return_value.first.return_value = teacher

        result = repo.get_teacher_by_user_id(1)

        assert result == teacher

    def test_get_teacher_by_user_id_not_found(self, repo, mock_db):
        """Test get_teacher_by_user_id returns None when not found."""

        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = repo.get_teacher_by_user_id(1)

        assert result is None

    def test_create_teacher(self, repo, mock_db):
        """Test create_teacher creates and flushes teacher."""

        result = repo.create_teacher(
            user_id=1,
            contract_type="FULL_TIME",
            department_id=1,
            active=True,
        )

        mock_db.add.assert_called_once()
        mock_db.flush.assert_called_once()
        assert result is not None

    def test_find_or_create_user_new_user(self, repo, mock_db):
        """Test find_or_create_user creates new user when not found."""

        mock_db.query.return_value.filter.return_value.first.return_value = None

        user_data = {
            "uid": "new-uid",
            "email": "new@example.com",
            "name": "New User",
            "active": True,
        }

        user, is_new = repo.find_or_create_user(user_data)

        assert is_new is True
        mock_db.add.assert_called_once()
        mock_db.flush.assert_called_once()

    def test_find_or_create_user_existing_by_uid(self, repo, mock_db, mock_user_model):
        """Test find_or_create_user returns existing user by uid."""

        mock_db.query.return_value.filter.return_value.first.return_value = (
            mock_user_model
        )

        user_data = {"uid": "test-uid-123", "email": "other@example.com"}

        user, is_new = repo.find_or_create_user(user_data)

        assert is_new is False
        assert user == mock_user_model

    def test_find_or_create_user_existing_by_email_updates_uid(
        self, repo, mock_db, mock_user_model
    ):
        """Test find_or_create_user updates uid if user exists by email."""

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query

        # First call returns None (by uid), second returns user (by email)
        mock_query.filter.side_effect = [
            MagicMock(first=MagicMock(return_value=None)),  # by uid
            MagicMock(first=MagicMock(return_value=mock_user_model)),  # by email
        ]

        user_data = {"uid": "new-uid", "email": "test@example.com"}

        user, is_new = repo.find_or_create_user(user_data)

        assert is_new is False
        assert mock_user_model.uid == "new-uid"

    def test_get_by_ids_empty_list(self, repo, mock_db):
        """Test get_by_ids returns empty list for empty input."""

        result = repo.get_by_ids([])

        assert result == []

    def test_get_by_uids_empty_list(self, repo, mock_db):
        """Test get_by_uids returns empty list for empty input."""

        result = repo.get_by_uids([])

        assert result == []

    def test_get_user_role_names_bulk(self, repo, mock_db):
        """Test get_user_role_names_bulk returns dict of roles by user."""

        mock_db.query.return_value.join.return_value.filter.return_value.all.return_value = [
            (1, "DOCENTE"),
            (1, "ADMIN"),
            (2, "DOCENTE"),
        ]

        result = repo.get_user_role_names_bulk([1, 2])

        assert result == {
            1: ["DOCENTE", "ADMIN"],
            2: ["DOCENTE"],
        }

    def test_get_user_role_names_bulk_empty(self, repo, mock_db):
        """Test get_user_role_names_bulk returns empty dict for empty input."""

        result = repo.get_user_role_names_bulk([])

        assert result == {}

    def test_search_no_filters(self, repo, mock_db, mock_user_model):
        """Test search with no filters returns all users paginated."""

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.options.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.offset.return_value.limit.return_value.all.return_value = [
            mock_user_model
        ]

        filters = UserFilters(search=None, active=None)
        pagination = PaginationParams(page=1, limit=10)

        items, total = repo.search(filters, pagination)

        assert total == 1
        assert items == [mock_user_model]
        mock_query.count.assert_called_once()
        mock_query.offset.assert_called_once_with(0)

    def test_search_with_search_filter(self, repo, mock_db, mock_user_model):
        """Test search applies ilike filter for search term."""

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.options.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.offset.return_value.limit.return_value.all.return_value = [
            mock_user_model
        ]

        filters = UserFilters(search="test", active=None)
        pagination = PaginationParams(page=1, limit=10)

        items, total = repo.search(filters, pagination)

        assert total == 1
        mock_query.filter.assert_called_once()

    def test_search_with_active_filter(self, repo, mock_db, mock_user_model):
        """Test search applies equality filter for active status."""

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.options.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.offset.return_value.limit.return_value.all.return_value = [
            mock_user_model
        ]

        filters = UserFilters(search=None, active=True)
        pagination = PaginationParams(page=1, limit=10)

        items, total = repo.search(filters, pagination)

        assert total == 1
        mock_query.filter.assert_called_once()

    def test_search_pagination_offset(self, repo, mock_db, mock_user_model):
        """Test search calculates correct offset for page > 1."""

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.options.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.count.return_value = 25
        mock_query.offset.return_value.limit.return_value.all.return_value = [
            mock_user_model
        ]

        filters = UserFilters(search=None, active=None)
        pagination = PaginationParams(page=3, limit=10)

        items, total = repo.search(filters, pagination)

        assert total == 25
        mock_query.offset.assert_called_once_with(20)


class TestBaseRepositoryPaginate:
    """Test suite for BaseRepository.paginate."""

    @pytest.fixture
    def repo(self, mock_db):
        return BaseRepository(UserModel, mock_db)

    def test_paginate_returns_items_and_total(self, repo, mock_db, mock_user_model):
        """Test paginate returns items list and total count."""

        mock_query = MagicMock()
        mock_query.count.return_value = 5
        mock_query.offset.return_value.limit.return_value.all.return_value = [
            mock_user_model
        ]

        pagination = PaginationParams(page=1, limit=10)
        items, total = repo.paginate(mock_query, pagination)

        assert total == 5
        assert items == [mock_user_model]
        mock_query.offset.assert_called_once_with(0)
        mock_query.offset.return_value.limit.assert_called_once_with(10)

    def test_paginate_correct_offset_for_page(self, repo, mock_db):
        """Test paginate calculates correct offset for given page."""
        mock_query = MagicMock()
        mock_query.count.return_value = 30
        mock_query.offset.return_value.limit.return_value.all.return_value = []

        pagination = PaginationParams(page=3, limit=10)
        repo.paginate(mock_query, pagination)

        mock_query.offset.assert_called_once_with(20)

    def test_paginate_empty_result(self, repo, mock_db):
        """Test paginate handles empty results."""
        mock_query = MagicMock()
        mock_query.count.return_value = 0
        mock_query.offset.return_value.limit.return_value.all.return_value = []

        pagination = PaginationParams(page=1, limit=10)
        items, total = repo.paginate(mock_query, pagination)

        assert total == 0
        assert items == []
