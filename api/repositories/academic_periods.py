"""
Academic periods repository
"""

from typing import Annotated

from fastapi.params import Depends
from sqlalchemy import or_
from sqlalchemy.orm import Session

from api.database import get_db
from api.models.academic_period import AcademicPeriodModel
from api.schemas.academic_period import (
    AcademicPeriodCreate,
    AcademicPeriodStatusUpdate,
    AcademicPeriodUpdate,
)
from api.serializers.academic_periods import academic_period_to_dict


class AcademicPeriodsRepository:
    """Academic periods repository"""

    def __init__(self, db: Session):
        self.db = db

    async def create(self, data: AcademicPeriodCreate) -> dict:
        """Create a new academic period."""

        period = AcademicPeriodModel(
            code=data.code,
            name=data.name,
            start_date=data.start_date,
            end_date=data.end_date,
            evaluation_end_date=data.evaluation_end_date,
            final_evaluation_date=data.final_evaluation_date,
            active=False,
        )

        self.db.add(period)
        self.db.commit()
        self.db.refresh(period)

        return academic_period_to_dict(period)

    async def get_all(
        self,
        search: str | None = None,
        page: int = 1,
        limit: int = 10,
    ) -> dict:
        """Get all academic periods with pagination and optional search filter."""

        query = self.db.query(AcademicPeriodModel)

        if search:
            term = search.strip()
            if term:
                like_term = f"%{term}%"
                query = query.filter(
                    or_(
                        AcademicPeriodModel.code.ilike(like_term),
                        AcademicPeriodModel.name.ilike(like_term),
                    )
                )

        total = query.count()
        pages = (total + limit - 1) // limit if total else 0
        offset = (page - 1) * limit

        periods = (
            query.order_by(AcademicPeriodModel.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        return {
            "items": [academic_period_to_dict(p) for p in periods],
            "total": total,
            "page": page,
            "limit": limit,
            "pages": pages,
        }

    async def get_by_id(self, period_id: int) -> dict | None:
        """Get an academic period by ID."""

        period = (
            self.db.query(AcademicPeriodModel)
            .filter(AcademicPeriodModel.id == period_id)
            .first()
        )

        if not period:
            return None

        return academic_period_to_dict(period)

    async def get_by_code(self, code: str) -> dict | None:
        """Get an academic period by code."""

        period = (
            self.db.query(AcademicPeriodModel)
            .filter(AcademicPeriodModel.code == code)
            .first()
        )

        if not period:
            return None

        return academic_period_to_dict(period)

    async def update(self, period_id: int, data: AcademicPeriodUpdate) -> dict | None:
        """Update an academic period's fields."""

        period = (
            self.db.query(AcademicPeriodModel)
            .filter(AcademicPeriodModel.id == period_id)
            .first()
        )

        if not period:
            return None

        payload = data.model_dump(exclude_unset=True)

        for field, value in payload.items():
            setattr(period, field, value)

        self.db.commit()
        self.db.refresh(period)

        return academic_period_to_dict(period)

    async def set_active(self, period_id: int) -> dict | None:
        """Activate a period and deactivate all others atomically."""

        period = (
            self.db.query(AcademicPeriodModel)
            .filter(AcademicPeriodModel.id == period_id)
            .first()
        )

        if not period:
            return None

        self.db.query(AcademicPeriodModel).update({AcademicPeriodModel.active: False})
        setattr(period, "active", True)

        self.db.commit()
        self.db.refresh(period)

        return academic_period_to_dict(period)

    async def close(self, period_id: int) -> dict | None:
        """Close (deactivate) an academic period."""

        period = (
            self.db.query(AcademicPeriodModel)
            .filter(AcademicPeriodModel.id == period_id)
            .first()
        )

        if not period:
            return None

        setattr(period, "active", False)

        self.db.commit()
        self.db.refresh(period)

        return academic_period_to_dict(period)

    async def update_status(
        self,
        period_id: int,
        data: AcademicPeriodStatusUpdate,
    ) -> dict | None:
        """Activate/deactivate an academic period by ID."""

        period = (
            self.db.query(AcademicPeriodModel)
            .filter(AcademicPeriodModel.id == period_id)
            .first()
        )

        if not period:
            return None

        setattr(period, "active", data.active)

        self.db.commit()
        self.db.refresh(period)

        return academic_period_to_dict(period)


def get_academic_periods_repository(db: Annotated[Session, Depends(get_db)]):
    """Get academic periods repository"""

    return AcademicPeriodsRepository(db)
