"""Tests for EvaluationQuestionScoresController layer."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from api.controllers.evaluation_question_scores import (
    EvaluationQuestionScoresController,
)


class TestEvaluationQuestionScoresController:
    """Test suite for EvaluationQuestionScoresController."""

    @pytest.fixture
    def mock_repository(self):
        """Mock EvaluationQuestionScoresRepository."""

        repo = MagicMock()
        repo.get_by_id = AsyncMock()
        repo.get_by_evaluation_score = AsyncMock()
        return repo

    @pytest.fixture
    def controller(self, mock_repository):
        """Create controller instance with mocked repository."""

        return EvaluationQuestionScoresController(mock_repository)

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
    async def test_get_by_evaluation_score_delegates_to_repository(
        self, controller, mock_repository
    ):
        """Test get_by_evaluation_score delegates to the repository."""

        mock_repository.get_by_evaluation_score.return_value = [{"id": 1}]

        result = await controller.get_by_evaluation_score(1)

        assert result == [{"id": 1}]
        mock_repository.get_by_evaluation_score.assert_awaited_once_with(1)
