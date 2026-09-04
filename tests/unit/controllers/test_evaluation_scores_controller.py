"""Tests for EvaluationScoresController layer."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from api.controllers.evaluation_scores import EvaluationScoresController


class TestEvaluationScoresController:
    """Test suite for EvaluationScoresController."""

    @pytest.fixture
    def mock_repository(self):
        """Mock EvaluationScoresRepository."""

        repo = MagicMock()
        repo.get_all = AsyncMock()
        repo.get_by_id = AsyncMock()
        repo.get_by_evaluation = AsyncMock()
        repo.get_by_evaluation_paginated = AsyncMock()
        return repo

    @pytest.fixture
    def controller(self, mock_repository):
        """Create controller instance with mocked repository."""

        return EvaluationScoresController(mock_repository)

    @pytest.mark.asyncio
    async def test_get_all_delegates_to_repository(self, controller, mock_repository):
        """Test get_all delegates to the repository."""

        mock_repository.get_all.return_value = [{"id": 1}]

        result = await controller.get_all()

        assert result == [{"id": 1}]

    @pytest.mark.asyncio
    async def test_get_by_id_delegates_to_repository(
        self, controller, mock_repository
    ):
        """Test get_by_id delegates to the repository."""

        mock_repository.get_by_id.return_value = {"id": 1}

        result = await controller.get_by_id(1)

        assert result == {"id": 1}
        mock_repository.get_by_id.assert_awaited_once_with(1)

    @pytest.mark.asyncio
    async def test_get_by_evaluation_delegates_to_repository(
        self, controller, mock_repository
    ):
        """Test get_by_evaluation delegates to the repository."""

        mock_repository.get_by_evaluation.return_value = [{"id": 1}]

        result = await controller.get_by_evaluation(1)

        assert result == [{"id": 1}]

    @pytest.mark.asyncio
    async def test_get_by_evaluation_paginated_delegates_to_repository(
        self, controller, mock_repository
    ):
        """Test get_by_evaluation_paginated forwards pagination and search."""

        mock_repository.get_by_evaluation_paginated.return_value = {"scores": []}

        result = await controller.get_by_evaluation_paginated(
            1, page=2, limit=5, search="Bases"
        )

        assert result == {"scores": []}
        mock_repository.get_by_evaluation_paginated.assert_awaited_once_with(
            1, page=2, limit=5, search="Bases"
        )
