"""Repository for department-related database operations."""

from typing import Annotated

from fastapi.params import Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from api.core.pagination import PaginationParams
from api.database import get_db
from api.models.department import DepartmentModel
from api.models.director import DirectorsModel
from api.models.teacher import TeacherModel
from api.models.user import UserModel
from api.repositories.base import BaseRepository
from api.schemas.department import DepartmentFilters


class DepartmentsRepository(BaseRepository[DepartmentModel]):
    """Repository for department-related database operations."""

    def __init__(self, db: Session):
        super().__init__(DepartmentModel, db)

    def get_by_id(self, department_id: int) -> DepartmentModel | None:
        """Get a department by ID."""

        return (
            self.db.query(DepartmentModel)
            .filter(DepartmentModel.id == department_id)
            .first()
        )

    def get_by_code(self, code: str) -> DepartmentModel | None:
        """Get a department by code."""

        return (
            self.db.query(DepartmentModel).filter(DepartmentModel.code == code).first()
        )

    def search(
        self,
        filters: DepartmentFilters,
        pagination: PaginationParams,
    ) -> tuple[list[DepartmentModel], int]:
        """Search for departments based on filters and pagination parameters."""

        query = self.db.query(DepartmentModel)

        if filters.search:
            term = filters.search.strip()

            if term:
                like_term = f"%{term}%"

                query = query.filter(
                    (DepartmentModel.name.ilike(like_term))
                    | (DepartmentModel.code.ilike(like_term))
                )

        if filters.active is not None:
            query = query.filter(DepartmentModel.active == filters.active)

        if filters.faculty_id is not None:
            query = query.filter(DepartmentModel.faculty_id == filters.faculty_id)

        query = query.order_by(DepartmentModel.created_at.desc())

        return self.paginate(query, pagination)

    def get_director_by_department_id(self, department_id: int) -> dict | None:
        """Get the active director of a department with user info."""

        result = (
            self.db.query(
                UserModel.id,
                UserModel.name,
                UserModel.avatar_url,
            )
            .select_from(UserModel)
            .join(DirectorsModel, DirectorsModel.user_id == UserModel.id)
            .filter(
                DirectorsModel.department_id == department_id,
                DirectorsModel.active == True,
            )
            .first()
        )

        if not result:
            return None

        return {
            "id": result.id,
            "name": result.name,
            "avatar_url": result.avatar_url,
        }

    def get_directors_by_department_ids(
        self, department_ids: list[int]
    ) -> dict[int, dict]:
        """Get active directors for multiple departments."""

        if not department_ids:
            return {}

        results = (
            self.db.query(
                UserModel.id,
                UserModel.name,
                UserModel.avatar_url,
                DirectorsModel.department_id,
            )
            .select_from(UserModel)
            .join(DirectorsModel, DirectorsModel.user_id == UserModel.id)
            .filter(
                DirectorsModel.department_id.in_(department_ids),
                DirectorsModel.active == True,
            )
            .all()
        )

        return {
            r.department_id: {
                "id": r.id,
                "name": r.name,
                "avatar_url": r.avatar_url,
            }
            for r in results
        }

    def count_teachers_by_department_ids(
        self, department_ids: list[int]
    ) -> dict[int, int]:
        """Count active teachers for multiple departments."""

        if not department_ids:
            return {}

        results = (
            self.db.query(
                TeacherModel.department_id,
                func.count(TeacherModel.id),
            )
            .filter(
                TeacherModel.department_id.in_(department_ids),
                TeacherModel.active == True,
            )
            .group_by(TeacherModel.department_id)
            .all()
        )

        return {r.department_id: r[1] for r in results}

    def has_active_teachers(self, department_id: int) -> bool:
        """Check if a department has active teachers assigned."""

        count = (
            self.db.query(TeacherModel)
            .filter(
                TeacherModel.department_id == department_id,
                TeacherModel.active == True,
            )
            .count()
        )

        return count > 0

    def has_active_director(self, department_id: int) -> bool:
        """Check if a department has an active director assigned."""

        count = (
            self.db.query(DirectorsModel)
            .filter(
                DirectorsModel.department_id == department_id,
                DirectorsModel.active == True,
            )
            .count()
        )

        return count > 0

    def update_department(
        self, department: DepartmentModel, data: dict
    ) -> DepartmentModel:
        """Update a department's fields."""

        for field, value in data.items():
            if value is not None:
                setattr(department, field, value)

        self.db.commit()
        self.db.refresh(department)

        return department

    def delete_department(self, department_id: int) -> DepartmentModel | None:
        """Delete a department by ID."""

        department = self.get_by_id(department_id)

        if not department:
            return None

        self.db.delete(department)
        self.db.commit()

        return department


def get_departments_repository(db: Annotated[Session, Depends(get_db)]):
    """Dependency injection for DepartmentsRepository."""

    return DepartmentsRepository(db)
