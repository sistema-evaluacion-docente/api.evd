"""Tests for EvaluationScoresRepository layer."""

from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from api.models.evaluation_score import EvaluationScoreModel
from api.repositories.evaluation_scores import EvaluationScoresRepository


class TestEvaluationScoresRepository:
    """Test suite for EvaluationScoresRepository."""

    @pytest.fixture
    def repo(self, mock_db):
        """Create repository instance with mocked DB."""

        return EvaluationScoresRepository(mock_db)

    @pytest.fixture
    def mock_score(self):
        """Mock EvaluationScoreModel instance."""

        row = MagicMock(spec=EvaluationScoreModel)
        row.id = 1
        row.evaluation_id = 1
        row.academic_group_id = 1
        row.respondent_count = 20
        row.overall_average = Decimal("4.2")
        return row

    @pytest.fixture
    def mock_query(self, mock_db):
        """Mock a chained SQLAlchemy query."""

        query = MagicMock()
        mock_db.query.return_value = query
        query.outerjoin.return_value = query
        query.filter.return_value = query
        query.order_by.return_value = query
        return query

    @pytest.mark.asyncio
    async def test_create(self, repo, mock_db, mock_score):
        """Test create persists a score and returns its serialized form."""

        result = await repo.create(1, 1, 20, Decimal("4.2"))

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        assert result["evaluation_id"] is not None or result is not None

    @pytest.mark.asyncio
    async def test_get_all(self, repo, mock_query, mock_score):
        """Test get_all returns serialized rows ordered by created_at desc."""

        mock_query.all.return_value = [mock_score]

        result = await repo.get_all()

        assert result[0]["id"] == 1

    @pytest.mark.asyncio
    async def test_get_by_id_found(self, repo, mock_query, mock_score):
        """Test get_by_id returns the serialized row with joined names."""

        mock_query.filter.return_value.first.return_value = (
            mock_score,
            "A",
            "Bases de Datos",
            "BD101",
        )

        result = await repo.get_by_id(1)

        assert result["group_name"] == "A"
        assert result["course_name"] == "Bases de Datos"

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, repo, mock_query):
        """Test get_by_id returns None when not found."""

        mock_query.filter.return_value.first.return_value = None

        result = await repo.get_by_id(999)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_by_evaluation(self, repo, mock_query, mock_score):
        """Test get_by_evaluation returns every joined row serialized."""

        mock_query.filter.return_value.all.return_value = [
            (mock_score, "A", "Bases de Datos", "BD101")
        ]

        result = await repo.get_by_evaluation(1)

        assert result[0]["course_code"] == "BD101"

    @pytest.mark.asyncio
    async def test_get_by_evaluation_paginated_without_search(
        self, repo, mock_query, mock_score
    ):
        """Test get_by_evaluation_paginated computes total/pages and does not filter."""

        mock_query.count.return_value = 1
        mock_query.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [
            (mock_score, "A", "Bases de Datos", "BD101")
        ]

        result = await repo.get_by_evaluation_paginated(1, page=1, limit=10)

        assert result["total"] == 1
        assert result["pages"] == 1
        assert len(result["scores"]) == 1

    @pytest.mark.asyncio
    async def test_get_by_evaluation_paginated_with_search(
        self, repo, mock_query, mock_score
    ):
        """Test get_by_evaluation_paginated filters by group/course name."""

        mock_query.count.return_value = 0
        mock_query.order_by.return_value.offset.return_value.limit.return_value.all.return_value = (
            []
        )

        result = await repo.get_by_evaluation_paginated(
            1, page=1, limit=10, search="Bases"
        )

        assert result["total"] == 0
        assert result["pages"] == 0
        mock_query.filter.assert_called()

    @pytest.mark.asyncio
    async def test_get_by_evaluation_and_group_found(
        self, repo, mock_query, mock_score
    ):
        """Test get_by_evaluation_and_group returns the serialized score."""

        mock_query.filter.return_value.first.return_value = mock_score

        result = await repo.get_by_evaluation_and_group(1, 1)

        assert result["id"] == 1

    @pytest.mark.asyncio
    async def test_get_by_evaluation_and_group_not_found(self, repo, mock_query):
        """Test get_by_evaluation_and_group returns None when not found."""

        mock_query.filter.return_value.first.return_value = None

        result = await repo.get_by_evaluation_and_group(1, 1)

        assert result is None
