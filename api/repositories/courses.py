"""Repository for course-related database operations."""

from typing import Annotated

from fastapi.params import Depends
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from api.core.pagination import PaginationParams
from api.database import get_db
from api.models.academic_group import AcademicGroupModel
from api.models.course import CourseModel
from api.repositories.base import BaseRepository
from api.schemas.course import CourseFilters


class CoursesRepository(BaseRepository[CourseModel]):
    """Repository for course-related database operations."""

    def __init__(self, db: Session):
        super().__init__(CourseModel, db)

    @staticmethod
    def _eager_options():
        """Eager-load department to avoid N+1 queries."""

        return (joinedload(CourseModel.department),)

    def get_by_id(self, course_id: int) -> CourseModel | None:
        """Get a course by ID with its relationships loaded."""

        return (
            self.db.query(CourseModel)
            .options(*self._eager_options())
            .filter(CourseModel.id == course_id)
            .first()
        )

    def get_by_code(self, code: str) -> CourseModel | None:
        """Get a course by code."""

        return (
            self.db.query(CourseModel)
            .options(*self._eager_options())
            .filter(CourseModel.code == code)
            .first()
        )

    def search(
        self,
        filters: CourseFilters,
        pagination: PaginationParams,
    ) -> tuple[list[CourseModel], int]:
        """Search for courses based on filters and pagination parameters."""

        query = self.db.query(CourseModel).options(*self._eager_options())

        if filters.search:
            term = filters.search.strip()

            if term:
                like_term = f"%{term}%"

                query = query.filter(
                    or_(
                        CourseModel.code.ilike(like_term),
                        CourseModel.name.ilike(like_term),
                    )
                )

        if filters.department_id is not None:
            query = query.filter(CourseModel.department_id == filters.department_id)

        query = query.order_by(CourseModel.created_at.desc())

        return self.paginate(query, pagination)

    def count_academic_groups(self, course_id: int) -> int:
        """Count academic groups associated with a course."""

        return (
            self.db.query(AcademicGroupModel)
            .filter(AcademicGroupModel.course_id == course_id)
            .count()
        )

    def update_course(self, course: CourseModel, data: dict) -> CourseModel:
        """Update a course's fields."""

        for field, value in data.items():
            if value is not None:
                setattr(course, field, value)

        self.db.commit()
        self.db.refresh(course)

        return course

    def delete_course(self, course_id: int) -> CourseModel | None:
        """Delete a course by ID."""

        course = self.get(course_id)

        if not course:
            return None

        self.db.delete(course)
        self.db.commit()

        return course


def get_courses_repository(
    db: Annotated[Session, Depends(get_db)],
) -> CoursesRepository:
    """Dependency injection for CoursesRepository."""

    return CoursesRepository(db)
