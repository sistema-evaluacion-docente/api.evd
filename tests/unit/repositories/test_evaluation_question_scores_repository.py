"""Tests for EvaluationQuestionScoresRepository layer."""

from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from api.models.evaluation_question_score import EvaluationQuestionScoreModel
from api.repositories.evaluation_question_scores import (
    EvaluationQuestionScoresRepository,
)


class TestEvaluationQuestionScoresRepository:
    """Test suite for EvaluationQuestionScoresRepository."""

    @pytest.fixture
    def repo(self, mock_db):
        """Create repository instance with mocked DB."""

        return EvaluationQuestionScoresRepository(mock_db)

    @pytest.fixture
    def mock_question_score(self):
        """Mock EvaluationQuestionScoreModel instance."""

        row = MagicMock(spec=EvaluationQuestionScoreModel)
        row.id = 1
        row.evaluation_score_id = 1
        row.question_code = "P1"
        row.score = Decimal("4.5")
        return row

    @pytest.mark.asyncio
    async def test_create(self, repo, mock_db, mock_question_score):
        """Test create persists the row and returns its serialized form."""

        mock_db.refresh.side_effect = lambda obj: None

        result = await repo.create(1, "P1", Decimal("4.5"))

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        assert result["question_code"] == "P1"
        assert result["score"] == Decimal("4.5")

    @pytest.mark.asyncio
    async def test_get_by_evaluation_score(
        self, repo, mock_db, mock_question_score
    ):
        """Test get_by_evaluation_score returns serialized rows in order."""

        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [
            mock_question_score
        ]

        result = await repo.get_by_evaluation_score(1)

        assert result == [
            {
                "id": 1,
                "evaluation_score_id": 1,
                "question_code": "P1",
                "score": Decimal("4.5"),
            }
        ]

    @pytest.mark.asyncio
    async def test_get_by_id_found(self, repo, mock_db, mock_question_score):
        """Test get_by_id returns the serialized row when found."""

        mock_db.query.return_value.filter.return_value.first.return_value = (
            mock_question_score
        )

        result = await repo.get_by_id(1)

        assert result["id"] == 1

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, repo, mock_db):
        """Test get_by_id returns None when not found."""

        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = await repo.get_by_id(999)

        assert result is None
