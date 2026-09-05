"""Tests for ComparisonRepository layer."""

from unittest.mock import MagicMock

import pytest

from api.repositories.comparison import ComparisonRepository


class TestComparisonRepository:
    """Test suite for ComparisonRepository."""

    @pytest.fixture
    def repo(self, mock_db):
        """Create repository instance with mocked DB."""

        return ComparisonRepository(mock_db)

    @pytest.fixture
    def mock_query(self, mock_db):
        """Mock a chained SQLAlchemy query."""

        query = MagicMock()
        mock_db.query.return_value = query
        query.join.return_value = query
        query.outerjoin.return_value = query
        query.filter.return_value = query
        query.group_by.return_value = query
        query.order_by.return_value = query
        return query

    @pytest.mark.asyncio
    async def test_get_teacher_info_found(self, repo, mock_query):
        """Test get_teacher_info returns a dict when the teacher exists."""

        row = MagicMock(teacher_id=1, teacher_name="Ana")
        mock_query.first.return_value = row

        result = await repo.get_teacher_info(1)

        assert result == {"teacher_id": 1, "teacher_name": "Ana"}

    @pytest.mark.asyncio
    async def test_get_teacher_info_not_found(self, repo, mock_query):
        """Test get_teacher_info returns None when the teacher does not exist."""

        mock_query.first.return_value = None

        result = await repo.get_teacher_info(999)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_period(self, repo, mock_query):
        """Test get_period returns the matched period model."""

        period = MagicMock()
        mock_query.first.return_value = period

        result = await repo.get_period(1)

        assert result == period

    @pytest.mark.asyncio
    async def test_get_overall_stats_with_data(self, repo, mock_query):
        """Test get_overall_stats rounds the average and defaults counts."""

        row = MagicMock(overall_average=4.256, group_count=2, respondent_count=30)
        mock_query.first.return_value = row

        result = await repo.get_overall_stats(1, 1)

        assert result == {
            "overall_average": 4.26,
            "group_count": 2,
            "respondent_count": 30,
        }

    @pytest.mark.asyncio
    async def test_get_overall_stats_with_no_average(self, repo, mock_query):
        """Test get_overall_stats defaults a missing average to None and zero counts."""

        row = MagicMock(overall_average=None, group_count=None, respondent_count=None)
        mock_query.first.return_value = row

        result = await repo.get_overall_stats(1, 1)

        assert result == {
            "overall_average": None,
            "group_count": 0,
            "respondent_count": 0,
        }

    @pytest.mark.asyncio
    async def test_get_question_averages(self, repo, mock_query):
        """Test get_question_averages maps question codes to rounded averages."""

        rows = [MagicMock(question_code="P1", avg_score=3.333)]
        mock_query.all.return_value = rows

        result = await repo.get_question_averages(1, 1)

        assert result == {"P1": 3.33}

    @pytest.mark.asyncio
    async def test_get_courses_with_data(self, repo, mock_query):
        """Test get_courses returns rounded averages and defaulted counts."""

        row = MagicMock(
            course_code="BD101",
            course_name="Bases de Datos",
            group_name="A",
            overall_average=4.256,
            respondent_count=20,
        )
        mock_query.all.return_value = [row]

        result = await repo.get_courses(1, 1)

        assert result == [
            {
                "course_code": "BD101",
                "course_name": "Bases de Datos",
                "group_name": "A",
                "overall_average": 4.26,
                "respondent_count": 20,
            }
        ]

    @pytest.mark.asyncio
    async def test_get_courses_with_no_average(self, repo, mock_query):
        """Test get_courses handles a missing average and respondent count."""

        row = MagicMock(
            course_code="BD101",
            course_name="Bases de Datos",
            group_name="A",
            overall_average=None,
            respondent_count=None,
        )
        mock_query.all.return_value = [row]

        result = await repo.get_courses(1, 1)

        assert result[0]["overall_average"] is None
        assert result[0]["respondent_count"] == 0

    @pytest.mark.asyncio
    async def test_get_comments_by_risk_with_rows(self, repo, mock_query):
        """Test get_comments_by_risk sums totals and builds the risk breakdown."""

        rows = [
            MagicMock(total=3, risk_name="ALTO", risk_count=2),
            MagicMock(total=3, risk_name=None, risk_count=1),
        ]
        mock_query.all.return_value = rows

        result = await repo.get_comments_by_risk(1, 1)

        assert result == {
            "total_comments": 6,
            "risk_breakdown": {"ALTO": 2, "SIN_CLASIFICAR": 1},
        }

    @pytest.mark.asyncio
    async def test_get_comments_by_risk_with_no_rows(self, repo, mock_query):
        """Test get_comments_by_risk returns None when there are no comments."""

        mock_query.all.return_value = []

        result = await repo.get_comments_by_risk(1, 1)

        assert result is None
