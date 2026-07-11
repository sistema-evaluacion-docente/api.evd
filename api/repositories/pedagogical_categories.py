"""
PedagogicalCategories repository
"""

from typing import Annotated

from fastapi.params import Depends
from sqlalchemy.orm import Session

from api.database import get_db
from api.models.pedagogical_category import PedagogicalCategoryModel


def _to_dict(obj: PedagogicalCategoryModel) -> dict:
    return {
        "id": obj.id,
        "name": obj.name,
        "description": obj.description,
        "color_hex": obj.color_hex,
        "created_at": obj.created_at,
        "updated_at": obj.updated_at,
    }


class PedagogicalCategoriesRepository:
    """PedagogicalCategories repository"""

    def __init__(self, db: Session):
        self.db = db

    async def get_all(self) -> list[dict]:
        """Return all pedagogical categories ordered by id."""

        rows = (
            self.db.query(PedagogicalCategoryModel)
            .order_by(PedagogicalCategoryModel.id)
            .all()
        )
        return [_to_dict(r) for r in rows]

    async def get_by_id(self, category_id: int) -> dict | None:
        """Return a single pedagogical category by id."""

        row = (
            self.db.query(PedagogicalCategoryModel)
            .filter(PedagogicalCategoryModel.id == category_id)
            .first()
        )
        return _to_dict(row) if row else None

    async def get_by_name(self, name: str) -> dict | None:
        """Return a category by exact name (case-insensitive)."""

        row = (
            self.db.query(PedagogicalCategoryModel)
            .filter(PedagogicalCategoryModel.name.ilike(name))
            .first()
        )
        return _to_dict(row) if row else None

    async def create(
        self,
        name: str,
        description: str | None = None,
        color_hex: str | None = None,
    ) -> dict:
        """Create a new pedagogical category."""

        row = PedagogicalCategoryModel(
            name=name, description=description, color_hex=color_hex
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return _to_dict(row)

    async def update(
        self,
        category_id: int,
        name: str | None = None,
        description: str | None = None,
        color_hex: str | None = None,
    ) -> dict | None:
        """Update an existing pedagogical category."""

        row = (
            self.db.query(PedagogicalCategoryModel)
            .filter(PedagogicalCategoryModel.id == category_id)
            .first()
        )
        if not row:
            return None

        if name is not None:
            row.name = name
        if description is not None:
            row.description = description
        if color_hex is not None:
            row.color_hex = color_hex

        self.db.commit()
        self.db.refresh(row)
        return _to_dict(row)

    async def delete(self, category_id: int) -> bool:
        """Delete a pedagogical category. Returns True if deleted, False if not found."""

        row = (
            self.db.query(PedagogicalCategoryModel)
            .filter(PedagogicalCategoryModel.id == category_id)
            .first()
        )
        if not row:
            return False

        self.db.delete(row)
        self.db.commit()
        return True


def get_pedagogical_categories_repository(db: Annotated[Session, Depends(get_db)]):
    """Get pedagogical categories repository"""

    return PedagogicalCategoriesRepository(db)
