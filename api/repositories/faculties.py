"""
Faculty repository module.
"""

from typing import Annotated

from fastapi import Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from api.core.pagination import PaginationParams
from api.database import get_db
from api.models.department import DepartmentModel
from api.models.faculty import FacultyModel
from api.repositories.base import BaseRepository
from api.schemas.faculty import FacultyCreate, FacultyFilters, FacultyUpdate


class FacultiesRepository(BaseRepository[FacultyModel]):
    """Repository for Faculty operations."""

    def __init__(self, db: Annotated[Session, Depends(get_db)]):
        super().__init__(FacultyModel, db)

    def get_by_code(self, code: str) -> FacultyModel | None:
        """Get a faculty by code."""

        return self.db.query(FacultyModel).filter(FacultyModel.code == code).first()

    def search(
        self, filters: FacultyFilters, pagination: PaginationParams
    ) -> tuple[list[FacultyModel], int]:
        """Search faculties with filters and pagination."""

        query = self.db.query(FacultyModel)

        if filters.search:
            search_term = f"%{filters.search}%"
            query = query.filter(
                (FacultyModel.name.ilike(search_term))
                | (FacultyModel.code.ilike(search_term))
            )

        if filters.active is not None:
            query = query.filter(FacultyModel.active == filters.active)

        return self.paginate(query, pagination)

    def get_department_counts(self, faculty_ids: list[int]) -> dict[int, int]:
        """Get department counts for multiple faculties."""

        if not faculty_ids:
            return {}

        results = (
            self.db.query(
                DepartmentModel.faculty_id,
                func.count(DepartmentModel.id),
            )
            .filter(DepartmentModel.faculty_id.in_(faculty_ids))
            .group_by(DepartmentModel.faculty_id)
            .all()
        )

        return {faculty_id: count for faculty_id, count in results}

    def has_departments(self, faculty_id: int) -> bool:
        """Check if a faculty has any departments."""

        count = (
            self.db.query(DepartmentModel)
            .filter(DepartmentModel.faculty_id == faculty_id)
            .count()
        )
        return count > 0

    def create_faculty(self, data: FacultyCreate) -> FacultyModel:
        """Create a new faculty."""

        faculty = FacultyModel(**data.model_dump())
        self.db.add(faculty)
        self.db.commit()
        self.db.refresh(faculty)
        return faculty

    def update_faculty(
        self, faculty: FacultyModel, data: FacultyUpdate
    ) -> FacultyModel:
        """Update a faculty."""

        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(faculty, key, value)

        self.db.commit()
        self.db.refresh(faculty)
        return faculty

    def delete_faculty(self, faculty: FacultyModel) -> None:
        """Delete a faculty."""

        self.db.delete(faculty)
        self.db.commit()


def get_faculties_repository(
    db: Annotated[Session, Depends(get_db)],
) -> FacultiesRepository:
    """Get faculties repository instance."""

    return FacultiesRepository(db)
