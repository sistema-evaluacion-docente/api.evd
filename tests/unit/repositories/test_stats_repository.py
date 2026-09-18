"""
Tests for StatsRepository layer.
"""

import datetime
from unittest.mock import MagicMock

import pytest

from api.repositories.stats import StatsRepository


def _chain(first=None, all_=None):
    """A query mock whose builder methods all return itself."""

    query = MagicMock()
    for method in ("filter", "order_by", "join", "group_by"):
        getattr(query, method).return_value = query
    query.first.return_value = first
    query.all.return_value = all_ if all_ is not None else []
    return query


def _department(id_, name, code="C"):
    department = MagicMock(id=id_, code=code)
    department.name = name
    return department


class TestStatsRepository:
    """Test suite for StatsRepository."""

    @pytest.mark.asyncio
    async def test_get_department_uploads_returns_none_for_a_missing_period(
        self, mock_db
    ):
        """Test an unknown academic period yields None (the route's 404)."""

        mock_db.query.side_effect = [_chain(first=None)]

        result = await StatsRepository(mock_db).get_department_uploads_by_period(99)

        assert result is None

    @pytest.mark.asyncio
    async def test_get_department_uploads_returns_empty_without_departments(
        self, mock_db
    ):
        """Test a scope with no active departments yields an empty list."""

        mock_db.query.side_effect = [_chain(first=MagicMock()), _chain(all_=[])]

        result = await StatsRepository(mock_db).get_department_uploads_by_period(1, 5)

        assert result == []

    @pytest.mark.asyncio
    async def test_get_department_uploads_flags_uploaded_and_missing_departments(
        self, mock_db
    ):
        """Test every department gets a row: uploaded ones carry the latest
        evaluation's state, the rest are flagged as not uploaded."""

        uploaded_at = datetime.datetime(2026, 3, 1)
        newest = MagicMock(
            department_id=1, created_at=uploaded_at, status="COMPLETED",
            ai_status="PENDING",
        )
        oldest = MagicMock(
            department_id=1, created_at=datetime.datetime(2026, 2, 1),
            status="COMPLETED", ai_status="COMPLETED",
        )

        mock_db.query.side_effect = [
            _chain(first=MagicMock()),
            _chain(all_=[_department(1, "Sistemas"), _department(2, "Civil")]),
            _chain(all_=[newest, oldest]),
            _chain(all_=[(1, 4.25)]),
        ]

        result = await StatsRepository(mock_db).get_department_uploads_by_period(1)

        assert result[0] == {
            "department_id": 1,
            "department_name": "Sistemas",
            "department_code": "C",
            "evaluation_count": 2,
            "has_uploaded": True,
            "last_uploaded_at": uploaded_at,
            "status": "COMPLETED",
            "ai_status": "PENDING",
            "global_average": 4.25,
        }
        assert result[1]["has_uploaded"] is False
        assert result[1]["evaluation_count"] == 0
        assert result[1]["ai_status"] is None
        assert result[1]["global_average"] is None

    @pytest.mark.asyncio
    async def test_get_department_uploads_uploaded_but_not_analysed_has_no_average(
        self, mock_db
    ):
        """Test an uploaded evaluation without scores yet still counts as
        uploaded, with a null average."""

        pending = MagicMock(
            department_id=1, created_at=datetime.datetime(2026, 3, 1),
            status="PROCESSING", ai_status="PENDING",
        )

        mock_db.query.side_effect = [
            _chain(first=MagicMock()),
            _chain(all_=[_department(1, "Sistemas")]),
            _chain(all_=[pending]),
            _chain(all_=[]),
        ]

        result = await StatsRepository(mock_db).get_department_uploads_by_period(1)

        assert result[0]["has_uploaded"] is True
        assert result[0]["global_average"] is None

    def test_get_department_comment_risk_counts_defaults_missing_levels_to_zero(
        self, mock_db
    ):
        """Test _get_department_comment_risk_counts fills in BAJO/MEDIO/ALTO
        with 0 when the department has no comments for that risk level."""

        repo = StatsRepository(mock_db)
        mock_db.query.return_value.join.return_value.join.return_value.filter.return_value.group_by.return_value.all.return_value = [
            ("ALTO", 3),
        ]

        result = repo._get_department_comment_risk_counts(1, [10, 11])

        assert result == {"BAJO": 0, "MEDIO": 0, "ALTO": 3}

    def test_get_department_comment_pedagogical_category_counts_returns_only_present_categories(
        self, mock_db
    ):
        """Test _get_department_comment_pedagogical_category_counts returns
        counts keyed by category name, without forcing a fixed catalogue
        (categories are DB-driven, unlike the fixed risk levels)."""

        repo = StatsRepository(mock_db)
        mock_db.query.return_value.join.return_value.join.return_value.join.return_value.filter.return_value.group_by.return_value.all.return_value = [
            ("LABEL_0", 5),
            ("LABEL_1", 2),
        ]

        result = repo._get_department_comment_pedagogical_category_counts(1, [10, 11])

        assert result == {"LABEL_0": 5, "LABEL_1": 2}
