"""Tests for RiskLevelsRepository layer."""

from unittest.mock import MagicMock

import pytest

from api.models.risk_level import RiskLevelModel
from api.repositories.risk_levels import RiskLevelsRepository


class TestRiskLevelsRepository:
    """Test suite for RiskLevelsRepository."""

    @pytest.fixture
    def repo(self, mock_db):
        """Create repository instance with mocked DB."""

        return RiskLevelsRepository(mock_db)

    @pytest.fixture
    def mock_row(self):
        """Mock RiskLevelModel instance."""

        row = MagicMock(spec=RiskLevelModel)
        row.id = 1
        row.name = "ALTO"
        row.description = "Riesgo alto"
        row.color_hex = "#FF0000"
        row.created_at = None
        row.updated_at = None
        return row

    @pytest.mark.asyncio
    async def test_get_all(self, repo, mock_db, mock_row):
        """Test get_all returns every risk level serialized, ordered by id."""

        mock_db.query.return_value.order_by.return_value.all.return_value = [mock_row]

        result = await repo.get_all()

        assert result == [
            {
                "id": 1,
                "name": "ALTO",
                "description": "Riesgo alto",
                "color_hex": "#FF0000",
                "created_at": None,
                "updated_at": None,
            }
        ]

    @pytest.mark.asyncio
    async def test_get_by_id_found(self, repo, mock_db, mock_row):
        """Test get_by_id returns the serialized row when found."""

        mock_db.query.return_value.filter.return_value.first.return_value = mock_row

        result = await repo.get_by_id(1)

        assert result["name"] == "ALTO"

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

        result = await repo.get_by_name("alto")

        assert result["id"] == 1

    @pytest.mark.asyncio
    async def test_get_by_name_not_found(self, repo, mock_db):
        """Test get_by_name returns None when not found."""

        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = await repo.get_by_name("inexistente")

        assert result is None

    @pytest.mark.asyncio
    async def test_create(self, repo, mock_db):
        """Test create persists a new risk level."""

        result = await repo.create("ALTO", "Riesgo alto", "#FF0000")

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        assert result is not None

    @pytest.mark.asyncio
    async def test_update_found(self, repo, mock_db, mock_row):
        """Test update overwrites only the given fields."""

        mock_db.query.return_value.filter.return_value.first.return_value = mock_row

        result = await repo.update(1, name="MEDIO")

        assert mock_row.name == "MEDIO"
        assert mock_row.description == "Riesgo alto"
        mock_db.commit.assert_called_once()
        assert result is not None

    @pytest.mark.asyncio
    async def test_update_not_found(self, repo, mock_db):
        """Test update returns None when the row does not exist."""

        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = await repo.update(999, name="MEDIO")

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
