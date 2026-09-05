"""Tests for PedagogicalCategoriesRepository layer."""

from unittest.mock import MagicMock

import pytest

from api.models.pedagogical_category import PedagogicalCategoryModel
from api.repositories.pedagogical_categories import PedagogicalCategoriesRepository


class TestPedagogicalCategoriesRepository:
    """Test suite for PedagogicalCategoriesRepository."""

    @pytest.fixture
    def repo(self, mock_db):
        """Create repository instance with mocked DB."""

        return PedagogicalCategoriesRepository(mock_db)

    @pytest.fixture
    def mock_row(self):
        """Mock PedagogicalCategoryModel instance."""

        row = MagicMock(spec=PedagogicalCategoryModel)
        row.id = 1
        row.name = "METODOLOGIA"
        row.description = "Metodología de enseñanza"
        row.color_hex = "#00FF00"
        row.created_at = None
        row.updated_at = None
        return row

    @pytest.mark.asyncio
    async def test_get_all(self, repo, mock_db, mock_row):
        """Test get_all returns every category serialized, ordered by id."""

        mock_db.query.return_value.order_by.return_value.all.return_value = [mock_row]

        result = await repo.get_all()

        assert result == [
            {
                "id": 1,
                "name": "METODOLOGIA",
                "description": "Metodología de enseñanza",
                "color_hex": "#00FF00",
                "created_at": None,
                "updated_at": None,
            }
        ]

    @pytest.mark.asyncio
    async def test_get_by_id_found(self, repo, mock_db, mock_row):
        """Test get_by_id returns the serialized row when found."""

        mock_db.query.return_value.filter.return_value.first.return_value = mock_row

        result = await repo.get_by_id(1)

        assert result["name"] == "METODOLOGIA"

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, repo, mock_db):
        """Test get_by_id returns None when not found."""

        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = await repo.get_by_id(999)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_name_found(self, repo, mock_db, mock_row):
        """Test get_by_name returns the serialized row when found."""

        mock_db.query.return_value.filter.return_value.first.return_value = mock_row

        result = await repo.get_by_name("metodologia")

        assert result["id"] == 1

    @pytest.mark.asyncio
    async def test_get_by_name_not_found(self, repo, mock_db):
        """Test get_by_name returns None when not found."""

        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = await repo.get_by_name("inexistente")

        assert result is None

    @pytest.mark.asyncio
    async def test_create(self, repo, mock_db):
        """Test create persists a new pedagogical category."""

        result = await repo.create("METODOLOGIA", "Metodología", "#00FF00")

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        assert result is not None

    @pytest.mark.asyncio
    async def test_update_found(self, repo, mock_db, mock_row):
        """Test update overwrites only the given fields."""

        mock_db.query.return_value.filter.return_value.first.return_value = mock_row

        result = await repo.update(1, description="Nueva descripción")

        assert mock_row.description == "Nueva descripción"
        assert mock_row.name == "METODOLOGIA"
        mock_db.commit.assert_called_once()
        assert result is not None

    @pytest.mark.asyncio
    async def test_update_not_found(self, repo, mock_db):
        """Test update returns None when the row does not exist."""

        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = await repo.update(999, description="Nueva descripción")

        assert result is None

    @pytest.mark.asyncio
    async def test_delete_found(self, repo, mock_db, mock_row):
        """Test delete removes the row and returns True."""

        mock_db.query.return_value.filter.return_value.first.return_value = mock_row

        result = await repo.delete(1)

        assert result is True
        mock_db.delete.assert_called_once_with(mock_row)
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_not_found(self, repo, mock_db):
        """Test delete returns False when the row does not exist."""

        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = await repo.delete(999)

        assert result is False
