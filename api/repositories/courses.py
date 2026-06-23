"""
Courses repository
"""

from typing import Annotated

from fastapi.params import Depends
from sqlalchemy.orm import Session

from api.database import get_db
from api.models.course import CourseModel
from api.schemas.course import CourseCreate, CourseUpdate
from api.serializers.courses import course_to_dict


class CoursesRepository:
    """Courses repository"""

    def __init__(self, db: Session):
        self.db = db

    async def create(self, data: CourseCreate) -> dict:
        """Create a new course."""

        course = CourseModel(
            code=data.code,
            name=data.name,
            department_id=data.department_id,
        )

        self.db.add(course)
        self.db.commit()
        self.db.refresh(course)

        return course_to_dict(course)

    async def get_all(self) -> list[dict]:
        """Get all courses ordered by creation date descending."""

        courses = (
            self.db.query(CourseModel)
            .order_by(CourseModel.created_at.desc())
            .all()
        )

        return [course_to_dict(c) for c in courses]

    async def get_by_id(self, course_id: int) -> dict | None:
        """Get a course by ID."""

        course = (
            self.db.query(CourseModel)
            .filter(CourseModel.id == course_id)
            .first()
        )

        if not course:
            return None

        return course_to_dict(course)

    async def get_by_code(self, code: str) -> dict | None:
        """Get a course by code."""

        course = (
            self.db.query(CourseModel)
            .filter(CourseModel.code == code)
            .first()
        )

        if not course:
            return None

        return course_to_dict(course)

    async def update(self, course_id: int, data: CourseUpdate) -> dict | None:
        """Update a course's fields."""

        course = (
            self.db.query(CourseModel)
            .filter(CourseModel.id == course_id)
            .first()
        )

        if not course:
            return None

        payload = data.model_dump(exclude_unset=True)

        for field, value in payload.items():
            setattr(course, field, value)

        self.db.commit()
        self.db.refresh(course)

        return course_to_dict(course)


def get_courses_repository(db: Annotated[Session, Depends(get_db)]):
    """Get courses repository"""

    return CoursesRepository(db)
