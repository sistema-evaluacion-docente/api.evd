"""Repository for academic period-related database operations."""

from datetime import date
from typing import Annotated

from fastapi.params import Depends
from sqlalchemy import or_
from sqlalchemy.orm import Session

from api.core.pagination import PaginationParams
from api.database import get_db
from api.models.academic_period import AcademicPeriodModel
from api.repositories.base import BaseRepository
from api.schemas.academic_period import AcademicPeriodFilters


class AcademicPeriodsRepository(BaseRepository[AcademicPeriodModel]):
    """Repository for academic period-related database operations."""

    def __init__(self, db: Session):
        super().__init__(AcademicPeriodModel, db)

    def get_by_code(self, code: str) -> AcademicPeriodModel | None:
        """Get an academic period by code."""

        return (
            self.db.query(AcademicPeriodModel)
            .filter(AcademicPeriodModel.code == code)
            .first()
        )

    def get_active(self) -> AcademicPeriodModel | None:
        """Get the currently active academic period."""

        return (
            self.db.query(AcademicPeriodModel)
            .filter(AcademicPeriodModel.active == True)
            .first()
        )

    def overlaps_with(
        self,
        start_date: date,
        end_date: date,
        exclude_id: int | None = None,
    ) -> bool:
        """Check if a date range overlaps with any existing period."""

        query = self.db.query(AcademicPeriodModel).filter(
            or_(
                AcademicPeriodModel.start_date.between(start_date, end_date),
                AcademicPeriodModel.end_date.between(start_date, end_date),
                (AcademicPeriodModel.start_date <= start_date)
                & (AcademicPeriodModel.end_date >= end_date),
            )
        )

        if exclude_id:
            query = query.filter(AcademicPeriodModel.id != exclude_id)

        return query.count() > 0

    def search(
        self,
        filters: AcademicPeriodFilters,
        pagination: PaginationParams,
    ) -> tuple[list[AcademicPeriodModel], int]:
        """Search for academic periods based on filters and pagination parameters."""

        query = self.db.query(AcademicPeriodModel)

        if filters.search:
            term = filters.search.strip()

            if term:
                like_term = f"%{term}%"

                query = query.filter(
                    or_(
                        AcademicPeriodModel.code.ilike(like_term),
                        AcademicPeriodModel.name.ilike(like_term),
                    )
                )

        if filters.active is not None:
            query = query.filter(AcademicPeriodModel.active == filters.active)

        query = query.order_by(AcademicPeriodModel.created_at.desc())

        return self.paginate(query, pagination)

    def create_period(self, data: dict) -> AcademicPeriodModel:
        """Create a new academic period."""

        return self.create(data)

    def update_period(
        self, period: AcademicPeriodModel, data: dict
    ) -> AcademicPeriodModel:
        """Update an academic period's fields."""

        for field, value in data.items():
            if value is not None:
                setattr(period, field, value)

        self.db.commit()
        self.db.refresh(period)

        return period

    def activate_period(self, period: AcademicPeriodModel) -> AcademicPeriodModel:
        """Activate an academic period."""

        period.active = True
        self.db.commit()
        self.db.refresh(period)

        return period

    def deactivate_all(self) -> None:
        """Deactivate all academic periods."""

        self.db.query(AcademicPeriodModel).update({AcademicPeriodModel.active: False})
        self.db.commit()

    def close_period(self, period: AcademicPeriodModel) -> AcademicPeriodModel:
        """Close (deactivate) an academic period."""

        period.active = False
        self.db.commit()
        self.db.refresh(period)

        return period

    def delete_period(self, period_id: int) -> AcademicPeriodModel | None:
        """Delete an academic period by ID."""

        period = self.get(period_id)

        if not period:
            return None

        self.db.delete(period)
        self.db.commit()

        return period

    def get_previous_period_code(self, code: str) -> str | None:
        """Get the previous academic period code from a code like '2025-2'."""

        parts = code.split("-")

        if len(parts) != 2:
            return None

        year = int(parts[0])
        semester = int(parts[1])

        if semester == 1:
            prev_year = year - 1
            prev_semester = 2
        else:
            prev_year = year
            prev_semester = semester - 1

        return f"{prev_year}-{prev_semester}"


def get_academic_periods_repository(
    db: Annotated[Session, Depends(get_db)],
) -> AcademicPeriodsRepository:
    """Dependency injection for AcademicPeriodsRepository."""

    return AcademicPeriodsRepository(db)
