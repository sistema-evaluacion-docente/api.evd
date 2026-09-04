"""Tests for BaseRepository — the CRUD/pagination behavior every repo inherits."""

from unittest.mock import MagicMock, patch

import pytest

from api.core.pagination import PaginationParams
from api.repositories.base import BaseRepository


class FakeModel:
    """Stand-in ORM model so BaseRepository doesn't need a real table."""

    id = MagicMock()

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
        self.id = kwargs.get("id", 1)


class TestBaseRepository:
    """Test suite for BaseRepository."""

    @pytest.fixture
    def repo(self, mock_db):
        """Create a BaseRepository instance for FakeModel."""

        return BaseRepository(FakeModel, mock_db)

    def test_get_queries_by_id(self, repo, mock_db):
        """Test get filters the model's table by id."""

        obj = FakeModel(id=1)
        mock_db.query.return_value.filter.return_value.first.return_value = obj

        result = repo.get(1)

        assert result == obj

    def test_list_applies_skip_and_limit(self, repo, mock_db):
        """Test list offsets and limits the query."""

        objs = [FakeModel(id=1)]
        mock_db.query.return_value.offset.return_value.limit.return_value.all.return_value = (
            objs
        )

        result = repo.list(skip=5, limit=20)

        assert result == objs
        mock_db.query.return_value.offset.assert_called_once_with(5)
        mock_db.query.return_value.offset.return_value.limit.assert_called_once_with(
            20
        )

    def test_create_from_a_plain_dict(self, repo, mock_db):
        """Test create builds the model straight from a dict payload."""

        result = repo.create({"name": "A"})

        assert result.name == "A"
        mock_db.add.assert_called_once()
        mock_db.flush.assert_called_once()

    def test_create_from_a_pydantic_like_object_with_model_dump(self, repo, mock_db):
        """Test create unpacks a payload exposing ``model_dump`` (pydantic v2)."""

        payload = MagicMock()
        payload.model_dump.return_value = {"name": "A"}

        result = repo.create(payload)

        assert result.name == "A"

    def test_create_from_an_object_with_dict_method(self, repo, mock_db):
        """Test create unpacks a payload only exposing ``.dict()`` (pydantic v1)."""

        class LegacyPayload:
            def dict(self):
                return {"name": "A"}

        result = repo.create(LegacyPayload())

        assert result.name == "A"

    def test_delete_removes_an_existing_record(self, repo, mock_db):
        """Test delete deletes and commits when the record exists."""

        obj = FakeModel(id=1)
        mock_db.query.return_value.filter.return_value.first.return_value = obj

        repo.delete(1)

        mock_db.delete.assert_called_once_with(obj)
        mock_db.commit.assert_called_once()

    def test_delete_noop_when_record_missing(self, repo, mock_db):
        """Test delete does nothing when the record does not exist."""

        mock_db.query.return_value.filter.return_value.first.return_value = None

        repo.delete(999)

        mock_db.delete.assert_not_called()
        mock_db.commit.assert_not_called()

    def test_paginate_returns_items_and_total(self, repo):
        """Test paginate offsets/limits the query and returns (items, total)."""

        query = MagicMock()
        query.count.return_value = 25
        query.offset.return_value.limit.return_value.all.return_value = ["a", "b"]
        pagination = PaginationParams(page=2, limit=10)

        items, total = repo.paginate(query, pagination)

        assert items == ["a", "b"]
        assert total == 25
        query.offset.assert_called_once_with(pagination.offset)

    def test_emit_db_event_noop_when_debug_disabled(self, repo):
        """Test _emit_db_event does nothing outside of DEBUG mode."""

        with patch("api.repositories.base.config") as mock_config:
            mock_config.DEBUG = False
            with patch("api.repositories.base.dev_logs_collector") as collector:
                repo._emit_db_event("INSERT", 1)

                collector.emit_db_write.assert_not_called()

    def test_emit_db_event_schedules_a_task_inside_a_running_loop(self, repo):
        """Test _emit_db_event uses ensure_future when a loop is already running."""

        with patch("api.repositories.base.config") as mock_config:
            mock_config.DEBUG = True
            with patch("api.repositories.base.dev_logs_collector") as collector:
                collector.emit_db_write.return_value = _noop_coro()

                async def _run():
                    repo._emit_db_event("INSERT", 1)

                import asyncio

                asyncio.run(_run())

                collector.emit_db_write.assert_called_once()

    def test_emit_db_event_swallows_unexpected_errors(self, repo):
        """Test _emit_db_event never lets a logging failure bubble up."""

        with patch("api.repositories.base.config") as mock_config:
            mock_config.DEBUG = True
            with patch(
                "api.repositories.base.dev_logs_collector"
            ) as collector:
                collector.emit_db_write.side_effect = RuntimeError("boom")

                repo._emit_db_event("INSERT", 1)  # must not raise


async def _noop_coro():
    """An already-resolved coroutine for mocking emit_db_write's return value."""

    return None
