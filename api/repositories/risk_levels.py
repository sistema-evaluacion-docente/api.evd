"""
RiskLevels repository
"""

from typing import Annotated

from fastapi.params import Depends
from sqlalchemy.orm import Session

from api.database import get_db
from api.models.risk_level import RiskLevelModel


def _to_dict(obj: RiskLevelModel) -> dict:
    return {
        "id": obj.id,
        "name": obj.name,
        "description": obj.description,
        "color_hex": obj.color_hex,
        "created_at": obj.created_at,
        "updated_at": obj.updated_at,
    }


class RiskLevelsRepository:
    """RiskLevels repository"""

    def __init__(self, db: Session):
        self.db = db

    async def get_all(self) -> list[dict]:
        """Return all risk levels ordered by id."""

        rows = self.db.query(RiskLevelModel).order_by(RiskLevelModel.id).all()
        return [_to_dict(r) for r in rows]

    async def get_by_id(self, risk_level_id: int) -> dict | None:
        """Return a single risk level by id."""

        row = (
            self.db.query(RiskLevelModel)
            .filter(RiskLevelModel.id == risk_level_id)
            .first()
        )
        return _to_dict(row) if row else None

    async def get_by_name(self, name: str) -> dict | None:
        """Return a risk level by exact name (case-insensitive)."""

        row = (
            self.db.query(RiskLevelModel)
            .filter(RiskLevelModel.name.ilike(name))
            .first()
        )
        return _to_dict(row) if row else None

    async def create(
        self,
        name: str,
        description: str | None = None,
        color_hex: str | None = None,
    ) -> dict:
        """Create a new risk level."""

        row = RiskLevelModel(name=name, description=description, color_hex=color_hex)
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return _to_dict(row)

    async def update(
        self,
        risk_level_id: int,
        name: str | None = None,
        description: str | None = None,
        color_hex: str | None = None,
    ) -> dict | None:
        """Update an existing risk level."""

        row = (
            self.db.query(RiskLevelModel)
            .filter(RiskLevelModel.id == risk_level_id)
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

    async def delete(self, risk_level_id: int) -> bool:
        """Delete a risk level. Returns True if deleted, False if not found."""

        row = (
            self.db.query(RiskLevelModel)
            .filter(RiskLevelModel.id == risk_level_id)
            .first()
        )
        if not row:
            return False

        self.db.delete(row)
        self.db.commit()
        return True


def get_risk_levels_repository(db: Annotated[Session, Depends(get_db)]):
    """Get risk levels repository"""

    return RiskLevelsRepository(db)
