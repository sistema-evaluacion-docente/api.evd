"""
Tests for DirectorsRepository layer.
"""

from unittest.mock import MagicMock

import pytest

from api.models.director import DirectorsModel
from api.models.user import UserModel
from api.models.teacher import TeacherModel
from api.models.department import DepartmentModel
from api.repositories.directors import DirectorsRepository


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

    @pytest.mark.asyncio
    async def test_assign_director_success(self, repo, mock_db, mock_director_model):
        """Test assign_director creates new director when none exists."""

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value.first.side_effect = [None, None]

        result = await repo.assign_director(10, 1)

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        assert result is not None

    @pytest.mark.asyncio
    async def test_assign_director_replaces_existing(
        self, repo, mock_db, mock_director_model
    ):
        """Test assign_director replaces existing director for department."""

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value.first.side_effect = [None, mock_director_model]

        result = await repo.assign_director(20, 1)

        assert mock_director_model.user_id == 20
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_assign_director_user_already_director_of_other_department(
        self, repo, mock_db, mock_director_model
    ):
        """Test assign_director raises when user is already director of another department."""

        mock_director_model.department_id = 2

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value.first.return_value = mock_director_model

        with pytest.raises(ValueError) as exc_info:
            await repo.assign_director(10, 1)

        assert "Este usuario ya es director de otro departamento" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_assign_director_same_department_no_error(
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

        result = await repo.assign_director(10, 1)

        mock_db.commit.assert_called_once()
        assert result is not None
