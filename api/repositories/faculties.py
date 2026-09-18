"""
Faculty repository module.
"""

from typing import Annotated

from fastapi import Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from api.core.pagination import PaginationParams
from api.database import get_db
from api.models.dean import DeanModel
from api.models.department import DepartmentModel
from api.models.faculty import FacultyModel
from api.models.user import UserModel
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

    def get_dean_by_faculty_id(self, faculty_id: int) -> DeanModel | None:
        """Get the dean of a faculty."""

        return (
            self.db.query(DeanModel).filter(DeanModel.faculty_id == faculty_id).first()
        )

    def get_dean_by_user_id(self, user_id: int) -> DeanModel | None:
        """Get the faculty a user is dean of, if any."""

        return self.db.query(DeanModel).filter(DeanModel.user_id == user_id).first()

    def assign_dean(self, user_id: int, faculty_id: int) -> DeanModel:
        """
        Assign a user as dean of a faculty. If the user is already dean of
        another faculty, raise an error. If the faculty already has a dean,
        update the existing row with the new user_id.
        """

        # `user_id` and `faculty_id` both carry a DB-level unique constraint,
        # and rows are never soft-deleted here (unassign deletes outright) —
        # see DirectorsRepository.assign_director for the same reasoning.
        existing_user_dean = (
            self.db.query(DeanModel).filter(DeanModel.user_id == user_id).first()
        )

        if (
            existing_user_dean
            and existing_user_dean.active
            and existing_user_dean.faculty_id != faculty_id
        ):
            raise ValueError("Este usuario ya es decano de otra facultad")

        existing_faculty_dean = (
            self.db.query(DeanModel).filter(DeanModel.faculty_id == faculty_id).first()
        )

        if existing_faculty_dean:
            existing_faculty_dean.user_id = user_id
            existing_faculty_dean.active = True
            self.db.commit()
            self.db.refresh(existing_faculty_dean)
            return existing_faculty_dean

        if existing_user_dean:
            existing_user_dean.faculty_id = faculty_id
            existing_user_dean.active = True
            self.db.commit()
            self.db.refresh(existing_user_dean)
            return existing_user_dean

        dean = DeanModel(user_id=user_id, faculty_id=faculty_id)
        self.db.add(dean)
        self.db.commit()
        self.db.refresh(dean)
        return dean

    def delete_dean(self, dean: DeanModel) -> None:
        """Delete a dean row."""

        self.db.delete(dean)
        self.db.commit()

    def get_dean_with_user_by_faculty_id(self, faculty_id: int) -> dict | None:
        """Get the active dean of a faculty, with user info."""

        result = (
            self.db.query(
                UserModel.id,
                UserModel.name,
                UserModel.avatar_url,
            )
            .select_from(UserModel)
            .join(DeanModel, DeanModel.user_id == UserModel.id)
            .filter(
                DeanModel.faculty_id == faculty_id,
                DeanModel.active == True,
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

    def get_deans_by_faculty_ids(self, faculty_ids: list[int]) -> dict[int, dict]:
        """Get active deans for multiple faculties."""

        if not faculty_ids:
            return {}

        results = (
            self.db.query(
                UserModel.id,
                UserModel.name,
                UserModel.avatar_url,
                DeanModel.faculty_id,
            )
            .select_from(UserModel)
            .join(DeanModel, DeanModel.user_id == UserModel.id)
            .filter(
                DeanModel.faculty_id.in_(faculty_ids),
                DeanModel.active == True,
            )
            .all()
        )

        return {
            r.faculty_id: {"id": r.id, "name": r.name, "avatar_url": r.avatar_url}
            for r in results
        }


def get_faculties_repository(
    db: Annotated[Session, Depends(get_db)],
) -> FacultiesRepository:
    """Get faculties repository instance."""

    return FacultiesRepository(db)
