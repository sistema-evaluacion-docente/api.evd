"""Tests for ImprovementPlansRepository layer."""

from unittest.mock import MagicMock

import pytest

from api.repositories.improvement_plans import ImprovementPlansRepository


class TestGetDepartmentContext:
    """Header data the creation page prefills the official forms with."""

    @pytest.fixture
    def repo(self, mock_db):
        """Create repository instance with mocked DB."""

        return ImprovementPlansRepository(mock_db)

    @pytest.fixture
    def mock_query(self, mock_db):
        """Mock the chained SQLAlchemy query the method builds."""

        query = MagicMock()
        mock_db.query.return_value = query
        query.select_from.return_value = query
        query.outerjoin.return_value = query
        query.filter.return_value = query
        return query

    def test_returns_department_and_faculty_names(self, repo, mock_query):
        """Test the department is joined all the way up to its faculty."""

        row = MagicMock()
        row.department_name = "Departamento de Sistemas"
        row.faculty_name = "Ingeniería"
        mock_query.first.return_value = row

        result = repo.get_department_context(3)

        assert result == {
            "department_name": "Departamento de Sistemas",
            "faculty_name": "Ingeniería",
        }

    def test_returns_empty_context_when_the_department_is_unknown(self, repo, mock_query):
        """Test a missing department answers with nulls, not an exception.

        The form falls back to what the director types, so a department without
        a row must not take the whole candidates response down with it.
        """

        mock_query.first.return_value = None

        result = repo.get_department_context(999)

        assert result == {"department_name": None, "faculty_name": None}
