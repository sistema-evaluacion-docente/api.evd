"""
Tests for ProgramsRepository layer.
"""

from unittest.mock import MagicMock

import pytest

from api.core.pagination import PaginationParams
from api.models.program import ProgramModel
from api.repositories.base import BaseRepository
from api.repositories.programs import ProgramsRepository
from api.schemas.program import ProgramCreate, ProgramFilters, ProgramUpdate


class TestProgramsRepository:
    """Test suite for ProgramsRepository."""

    @pytest.fixture
    def repo(self, mock_db):
        """Create repository instance with mocked DB."""

        return ProgramsRepository(mock_db)

    @pytest.fixture
    def mock_program_model(self):
        """Mock ProgramModel instance."""

        program = MagicMock(spec=ProgramModel)
        program.id = 1
        program.name = "Ingeniería de Sistemas"
        program.code = "IS"
        program.active = True
        return program

    @pytest.fixture
    def mock_query(self, mock_db, mock_program_model):
        """Query chain returning a single program."""

        query = MagicMock()
        mock_db.query.return_value = query
        query.filter.return_value = query
        query.count.return_value = 1
        query.offset.return_value.limit.return_value.all.return_value = [
            mock_program_model
        ]
        return query

    def test_inherits_base_repository(self, repo):
        """Test ProgramsRepository inherits from BaseRepository."""

        assert isinstance(repo, BaseRepository)

    def test_get_by_code_when_program_exists_returns_program(
        self, repo, mock_db, mock_program_model
    ):
        """Test get_by_code returns program when found."""

        mock_db.query.return_value.filter.return_value.first.return_value = (
            mock_program_model
        )

        result = repo.get_by_code("IS")

        assert result == mock_program_model

    def test_get_by_code_when_program_missing_returns_none(self, repo, mock_db):
        """Test get_by_code returns None when not found."""

        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = repo.get_by_code("NONEXISTENT")

        assert result is None

    def test_search_without_filters_returns_all_paginated(
        self, repo, mock_query, mock_program_model
    ):
        """Test search with no filters returns all programs paginated."""

        items, total = repo.search(ProgramFilters(), PaginationParams(page=1, limit=10))

        assert total == 1
        assert items == [mock_program_model]
        mock_query.filter.assert_not_called()
        mock_query.offset.assert_called_once_with(0)

    def test_search_with_search_term_applies_one_filter(self, repo, mock_query):
        """Test search applies an ilike filter for the search term."""

        items, total = repo.search(
            ProgramFilters(search="Sistemas"), PaginationParams(page=1, limit=10)
        )

        assert total == 1
        mock_query.filter.assert_called_once()

    def test_search_with_active_filter_applies_one_filter(self, repo, mock_query):
        """Test search applies an equality filter for active status."""

        items, total = repo.search(
            ProgramFilters(active=True), PaginationParams(page=1, limit=10)
        )

        assert total == 1
        mock_query.filter.assert_called_once()

    def test_search_with_both_filters_applies_two_filters(self, repo, mock_query):
        """Test search stacks the search term and the active filter."""

        repo.search(
            ProgramFilters(search="Sistemas", active=False),
            PaginationParams(page=1, limit=10),
        )

        assert mock_query.filter.call_count == 2

    def test_search_on_later_page_offsets_results(self, repo, mock_query):
        """Test search calculates the correct offset for page > 1."""

        mock_query.count.return_value = 25

        items, total = repo.search(ProgramFilters(), PaginationParams(page=3, limit=10))

        assert total == 25
        mock_query.offset.assert_called_once_with(20)

    def test_create_program_adds_commits_and_refreshes(self, repo, mock_db):
        """Test create_program persists the program and returns it refreshed."""

        data = ProgramCreate(name="Ingeniería de Sistemas", code="IS")

        result = repo.create_program(data)

        assert result.name == "Ingeniería de Sistemas"
        assert result.code == "IS"
        mock_db.add.assert_called_once_with(result)
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once_with(result)

    def test_update_program_only_sets_provided_fields(
        self, repo, mock_db, mock_program_model
    ):
        """Test update_program ignores fields absent from the payload."""

        data = ProgramUpdate(name="Ingeniería Industrial")

        result = repo.update_program(mock_program_model, data)

        assert result.name == "Ingeniería Industrial"
        assert result.code == "IS"
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once_with(mock_program_model)

    def test_delete_program_deletes_and_commits(
        self, repo, mock_db, mock_program_model
    ):
        """Test delete_program removes the program and commits."""

        repo.delete_program(mock_program_model)

        mock_db.delete.assert_called_once_with(mock_program_model)
        mock_db.commit.assert_called_once()
