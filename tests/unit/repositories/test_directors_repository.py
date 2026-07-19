"""
Tests for DirectorsRepository layer.
"""

from unittest.mock import MagicMock

import pytest

from api.models.director import DirectorsModel
from api.repositories.directors import DirectorsRepository
from api.repositories.base import BaseRepository
from api.schemas.director import DirectorFilters
from api.core.pagination import PaginationParams


class TestDirectorsRepository:
    """Test suite for DirectorsRepository."""

    @pytest.fixture
    def repo(self, mock_db):
        """Create repository instance with mocked DB."""

        return DirectorsRepository(mock_db)

    @pytest.fixture
    def mock_director_model(self):
        """Mock DirectorsModel instance."""

        director = MagicMock(spec=DirectorsModel)
        director.id = 1
        director.user_id = 10
        director.department_id = 1
        director.active = True
        return director

    def test_inherits_base_repository(self, repo):
        """Test DirectorsRepository inherits from BaseRepository."""

        assert isinstance(repo, BaseRepository)

    def test_assign_director_success(self, repo, mock_db, mock_director_model):
        """Test assign_director creates new director when none exists."""

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value.first.side_effect = [None, None]

        result = repo.assign_director(10, 1)

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        assert result is not None

    def test_assign_director_replaces_existing(
        self, repo, mock_db, mock_director_model
    ):
        """Test assign_director replaces existing director for department."""

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value.first.side_effect = [None, mock_director_model]

        result = repo.assign_director(20, 1)

        assert mock_director_model.user_id == 20
        mock_db.commit.assert_called_once()

    def test_assign_director_user_already_director_of_other_department(
        self, repo, mock_db, mock_director_model
    ):
        """Test assign_director raises when user is already director of another department."""

        mock_director_model.department_id = 2

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value.first.return_value = mock_director_model

        with pytest.raises(ValueError) as exc_info:
            repo.assign_director(10, 1)

        assert "Este usuario ya es director de otro departamento" in str(exc_info.value)

    def test_assign_director_same_department_no_error(
        self, repo, mock_db, mock_director_model
    ):
        """Test assign_director succeeds when user is already director of same department."""

        mock_director_model.department_id = 1

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value.first.side_effect = [
            mock_director_model,
            mock_director_model,
        ]

        result = repo.assign_director(10, 1)

        mock_db.commit.assert_called_once()
        assert result is not None

    def test_get_by_department_id_found(self, repo, mock_db, mock_director_model):
        """Test get_by_department_id returns director when found."""

        mock_db.query.return_value.filter.return_value.first.return_value = (
            mock_director_model
        )

        result = repo.get_by_department_id(1)

        assert result == mock_director_model

    def test_get_by_department_id_not_found(self, repo, mock_db):
        """Test get_by_department_id returns None when not found."""

        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = repo.get_by_department_id(999)

        assert result is None

    def test_get_by_user_id_found(self, repo, mock_db, mock_director_model):
        """Test get_by_user_id returns director when found."""

        mock_db.query.return_value.filter.return_value.first.return_value = (
            mock_director_model
        )

        result = repo.get_by_user_id(10)

        assert result == mock_director_model

    def test_get_by_user_id_not_found(self, repo, mock_db):
        """Test get_by_user_id returns None when not found."""

        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = repo.get_by_user_id(999)

        assert result is None

    def test_search_no_filters(self, repo, mock_db, mock_director_model):
        """Test search with no filters returns all directors paginated."""

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.join.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.offset.return_value.limit.return_value.all.return_value = [
            mock_director_model
        ]

        filters = DirectorFilters()
        pagination = PaginationParams(page=1, limit=10)

        items, total = repo.search(filters, pagination)

        assert total == 1
        assert items == [mock_director_model]
        mock_query.count.assert_called_once()
        mock_query.offset.assert_called_once_with(0)

    def test_search_with_search_filter(self, repo, mock_db, mock_director_model):
        """Test search applies ilike filter for search term."""

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.join.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.offset.return_value.limit.return_value.all.return_value = [
            mock_director_model
        ]

        filters = DirectorFilters(search="test")
        pagination = PaginationParams(page=1, limit=10)

        items, total = repo.search(filters, pagination)

        assert total == 1
        mock_query.filter.assert_called_once()

    def test_search_with_active_filter(self, repo, mock_db, mock_director_model):
        """Test search applies equality filter for active status."""

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.join.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.offset.return_value.limit.return_value.all.return_value = [
            mock_director_model
        ]

        filters = DirectorFilters(active=True)
        pagination = PaginationParams(page=1, limit=10)

        items, total = repo.search(filters, pagination)

        assert total == 1

    def test_update_director(self, repo, mock_db, mock_director_model):
        """Test update_director updates attributes."""

        from api.schemas.director import DirectorUpdate

        data = DirectorUpdate(active=False)
        result = repo.update_director(mock_director_model, data)

        assert mock_director_model.active is False
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once_with(mock_director_model)
        assert result == mock_director_model

    def test_delete_director(self, repo, mock_db, mock_director_model):
        """Test delete_director deletes director."""

        repo.delete_director(mock_director_model)

        mock_db.delete.assert_called_once_with(mock_director_model)
        mock_db.commit.assert_called_once()
