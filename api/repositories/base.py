"""Base repository for common database operations."""

from __future__ import annotations

import asyncio
import logging
from typing import Generic, TypeVar

from sqlalchemy.orm import Session

from api.config import config
from api.core.pagination import PaginationParams
from api.core.dev_logs.collector import dev_logs_collector

logger = logging.getLogger(__name__)

ModelType = TypeVar("ModelType")


class BaseRepository(Generic[ModelType]):
    """Base repository for common database operations."""

    def __init__(self, model: type[ModelType], db: Session):
        self.model = model
        self.db = db

    def _emit_db_event(self, operation: str, record_id: int | None = None) -> None:
        """Emit a database event for development logging purposes."""

        if not config.DEBUG:
            return

        try:
            model_name = self.model.__name__.replace("Model", "")

            try:
                asyncio.get_running_loop()

                asyncio.ensure_future(
                    dev_logs_collector.emit_db_write(
                        operation=operation,
                        model=model_name,
                        record_id=record_id,
                    )
                )
            except RuntimeError:
                asyncio.run(
                    dev_logs_collector.emit_db_write(
                        operation=operation,
                        model=model_name,
                        record_id=record_id,
                    )
                )
        except Exception:
            pass

    def get(self, id: int) -> ModelType | None:
        """Retrieve a record by its ID."""

        return self.db.query(self.model).filter(self.model.id == id).first()

    def list(self, skip: int = 0, limit: int = 100) -> list[ModelType]:
        """Retrieve a list of records with optional pagination."""

        return self.db.query(self.model).offset(skip).limit(limit).all()

    def create(self, data: dict) -> ModelType:
        """
        Create a new record in the database.
        """

        if hasattr(data, "model_dump"):
            data = data.model_dump()
        elif hasattr(data, "dict"):
            data = data.dict()

        obj = self.model(**data)
        self.db.add(obj)
        self.db.flush()

        self._emit_db_event("INSERT", getattr(obj, "id", None))

        return obj

    def delete(self, id: int) -> None:
        """Delete a record by its ID."""

        obj = self.get(id)

        if obj:
            self.db.delete(obj)
            self.db.commit()
            self._emit_db_event("DELETE", id)

    def paginate(
        self, query, pagination: PaginationParams
    ) -> tuple[list[ModelType], int]:
        """Paginate the results of a query based on the provided pagination parameters."""

        total = query.count()
        items = query.offset(pagination.offset).limit(pagination.limit).all()

        return items, total
