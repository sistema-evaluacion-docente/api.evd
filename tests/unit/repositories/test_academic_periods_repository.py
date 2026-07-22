"""Tests for AcademicPeriodsRepository layer."""

from datetime import date
from unittest.mock import MagicMock

import pytest

from api.core.pagination import PaginationParams
from api.models.academic_period import AcademicPeriodModel
from api.repositories.academic_periods import AcademicPeriodsRepository
from api.repositories.base import BaseRepository
from api.schemas.academic_period import AcademicPeriodFilters


class TestAcademicPeriodsRepository:
    """Test suite for AcademicPeriodsRepository."""

    @pytest.fixture
    def repo(self, mock_db):
        """Create repository instance with mocked DB."""

        return AcademicPeriodsRepository(mock_db)

    @pytest.fixture
    def mock_period_model(self):
        """Mock AcademicPeriodModel instance."""

        period = MagicMock(spec=AcademicPeriodModel)
        period.id = 1
        period.code = "2024-1"
        period.name = "Primer semestre 2024"
        period.start_date = date(2024, 1, 15)
        period.end_date = date(2024, 6, 15)
        period.evaluation_end_date = date(2024, 6, 30)
        period.final_evaluation_date = date(2024, 7, 15)
        period.active = False
        return period

    def test_inherits_base_repository(self, repo):
        """Test AcademicPeriodsRepository inherits from BaseRepository."""

        assert isinstance(repo, BaseRepository)

    def test_get_by_code_found(self, repo, mock_db, mock_period_model):
        """Test get_by_code returns period when found."""

        mock_db.query.return_value.filter.return_value.first.return_value = (
            mock_period_model
        )

        result = repo.get_by_code("2024-1")

        assert result == mock_period_model

    def test_get_by_code_not_found(self, repo, mock_db):
        """Test get_by_code returns None when not found."""

        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = repo.get_by_code("NONEXISTENT")

        assert result is None

    def test_get_active_found(self, repo, mock_db, mock_period_model):
        """Test get_active returns active period when found."""

        mock_period_model.active = True
        mock_db.query.return_value.filter.return_value.first.return_value = (
            mock_period_model
        )

        result = repo.get_active()

        assert result == mock_period_model

    def test_get_active_not_found(self, repo, mock_db):
        """Test get_active returns None when no active period."""

        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = repo.get_active()

        assert result is None

    def test_overlaps_with_true(self, repo, mock_db):
        """Test overlaps_with returns True when overlap exists."""

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 1

        result = repo.overlaps_with(date(2024, 5, 1), date(2024, 10, 1))

        assert result is True

    def test_overlaps_with_false(self, repo, mock_db):
        """Test overlaps_with returns False when no overlap."""

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 0

        result = repo.overlaps_with(date(2025, 1, 1), date(2025, 6, 1))

        assert result is False

    def test_overlaps_with_exclude_id(self, repo, mock_db):
        """Test overlaps_with excludes specified ID."""

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.count.return_value = 0

        result = repo.overlaps_with(date(2024, 5, 1), date(2024, 10, 1), exclude_id=1)

        assert result is False
        mock_query.filter.assert_called()

    def test_search_no_filters(self, repo, mock_db, mock_period_model):
        """Test search with no filters returns all periods paginated."""

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.offset.return_value.limit.return_value.all.return_value = [
            mock_period_model
        ]

        filters = AcademicPeriodFilters()
        pagination = PaginationParams(page=1, limit=10)

        items, total = repo.search(filters, pagination)

        assert total == 1
        assert items == [mock_period_model]
        mock_query.count.assert_called_once()
        mock_query.offset.assert_called_once_with(0)

    def test_search_with_search_filter(self, repo, mock_db, mock_period_model):
        """Test search applies ilike filter for search term."""

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.offset.return_value.limit.return_value.all.return_value = [
            mock_period_model
        ]

        filters = AcademicPeriodFilters(search="2024")
        pagination = PaginationParams(page=1, limit=10)

        items, total = repo.search(filters, pagination)

        assert total == 1
        mock_query.filter.assert_called()

    def test_search_with_active_filter(self, repo, mock_db, mock_period_model):
        """Test search applies equality filter for active status."""

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.count.return_value = 1
        mock_query.offset.return_value.limit.return_value.all.return_value = [
            mock_period_model
        ]

        filters = AcademicPeriodFilters(active=True)
        pagination = PaginationParams(page=1, limit=10)

        items, total = repo.search(filters, pagination)

        assert total == 1

    def test_search_pagination_offset(self, repo, mock_db, mock_period_model):
        """Test search calculates correct offset for page > 1."""

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.count.return_value = 25
        mock_query.offset.return_value.limit.return_value.all.return_value = [
            mock_period_model
        ]

        filters = AcademicPeriodFilters()
        pagination = PaginationParams(page=3, limit=10)

        items, total = repo.search(filters, pagination)

        assert total == 25
        mock_query.offset.assert_called_once_with(20)

    def test_create_period(self, repo, mock_db, mock_period_model):
        """Test create_period creates and returns period."""

        repo.create = MagicMock(return_value=mock_period_model)

        result = repo.create_period(
            {
                "code": "2024-1",
                "name": "Primer semestre 2024",
                "start_date": date(2024, 1, 15),
                "end_date": date(2024, 6, 15),
            }
        )

        repo.create.assert_called_once()
        assert result == mock_period_model

    def test_update_period(self, repo, mock_db, mock_period_model):
        """Test update_period updates attributes."""

        result = repo.update_period(mock_period_model, {"name": "Nuevo nombre"})

        assert mock_period_model.name == "Nuevo nombre"
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once_with(mock_period_model)
        assert result == mock_period_model

    def test_activate_period(self, repo, mock_db, mock_period_model):
        """Test activate_period sets active to True."""

        result = repo.activate_period(mock_period_model)

        assert mock_period_model.active is True
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once_with(mock_period_model)
        assert result == mock_period_model

    def test_deactivate_all(self, repo, mock_db):
        """Test deactivate_all sets all periods to inactive."""

        mock_query = MagicMock()
        mock_db.query.return_value = mock_query
        mock_query.update.return_value = 5

        repo.deactivate_all()

        mock_query.update.assert_called_once()
        mock_db.commit.assert_called_once()

    def test_close_period(self, repo, mock_db, mock_period_model):
        """Test close_period sets active to False."""

        mock_period_model.active = True
        result = repo.close_period(mock_period_model)

        assert mock_period_model.active is False
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once_with(mock_period_model)
        assert result == mock_period_model

    def test_delete_period_success(self, repo, mock_db, mock_period_model):
        """Test delete_period deletes and returns period."""

        mock_db.query.return_value.filter.return_value.first.return_value = (
            mock_period_model
        )

        result = repo.delete_period(1)

        assert result == mock_period_model
        mock_db.delete.assert_called_once_with(mock_period_model)
        mock_db.commit.assert_called_once()

    def test_delete_period_not_found(self, repo, mock_db):
        """Test delete_period returns None when not found."""

        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = repo.delete_period(999)

        assert result is None

    def test_get_previous_period_code_first_semester(self, repo):
        """Test get_previous_period_code for first semester."""

        result = repo.get_previous_period_code("2024-1")

        assert result == "2023-2"

    def test_get_previous_period_code_second_semester(self, repo):
        """Test get_previous_period_code for second semester."""

        result = repo.get_previous_period_code("2024-2")

        assert result == "2024-1"

    def test_get_previous_period_code_invalid_format(self, repo):
        """Test get_previous_period_code returns None for invalid format."""

        result = repo.get_previous_period_code("INVALID")

        assert result is None
