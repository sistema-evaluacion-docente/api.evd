"""Base repository for common database operations."""

from __future__ import annotations

from typing import Generic, TypeVar

from sqlalchemy.orm import Session

from api.core.pagination import PaginationParams

ModelType = TypeVar("ModelType")


class BaseRepository(Generic[ModelType]):
    """Base repository for common database operations."""

    def __init__(self, model: type[ModelType], db: Session):
        self.model = model
        self.db = db

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

        return obj

    def delete(self, id: int) -> None:
        """Delete a record by its ID."""

        obj = self.get(id)

        if obj:
            self.db.delete(obj)
            self.db.commit()

    def paginate(
        self, query, pagination: PaginationParams
    ) -> tuple[list[ModelType], int]:
        """Paginate the results of a query based on the provided pagination parameters."""

        total = query.count()
        items = query.offset(pagination.offset).limit(pagination.limit).all()

        return items, total
