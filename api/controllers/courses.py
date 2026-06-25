"""
Courses controller
"""

from fastapi.param_functions import Depends

from api.repositories.audits import AuditsRepository, get_audits_repository
from api.repositories.courses import CoursesRepository, get_courses_repository
from api.repositories.users import UsersRepository, get_users_repository
from api.schemas.audit import AuditCreate
from api.schemas.course import CourseCreate, CourseUpdate


class CoursesController:
    """Courses controller"""

    def __init__(
        self,
        repository: CoursesRepository,
        audits_repository: AuditsRepository,
        users_repository: UsersRepository,
    ):
        self.repository = repository
        self.audits_repository = audits_repository
        self.users_repository = users_repository

    async def _resolve_user_id(self, current_user) -> int | None:
        user = await self.users_repository.get_by_uid(current_user.uid)
        return user["id"] if user else None

    async def create(self, data: CourseCreate, current_user) -> dict:
        """Create a new course, rejecting duplicate codes."""

        existing = await self.repository.get_by_code(data.code)

        if existing:
            raise ValueError(
                f"A course with code '{data.code}' already exists"
            )

        course = await self.repository.create(data)

        await self.audits_repository.create(
            AuditCreate(
                user_id=await self._resolve_user_id(current_user),
                table_name="courses",
                operation="CREATE",
                element=f"Course {course.get('id')}",
                description=f"Se creó el curso {data.code} (nombre: {data.name}, departamento: {data.department_id})",
                created_at=None,
            )
        )

        return course

    async def get_all(self) -> list[dict]:
        """Get all courses."""

        return await self.repository.get_all()

    async def get_by_id(self, course_id: int) -> dict | None:
        """Get a course by ID."""

        return await self.repository.get_by_id(course_id)

    async def update(
        self, course_id: int, data: CourseUpdate, current_user
    ) -> dict | None:
        """Update a course's fields."""

        course = await self.repository.get_by_id(course_id)

        if not course:
            return None

        updated = await self.repository.update(course_id, data)

        changes = []
        for field in ("name", "department_id"):
            new_val = getattr(data, field, None)
            if new_val is not None and new_val != course.get(field):
                old_val = course.get(field)
                changes.append(f"{field} cambió de {old_val} a {new_val}")
        desc = "Se actualizó el curso #" + str(course_id)
        if changes:
            desc += ": " + "; ".join(changes)
        else:
            desc += ": No se realizaron cambios"
        await self.audits_repository.create(
            AuditCreate(
                user_id=await self._resolve_user_id(current_user),
                table_name="courses",
                operation="UPDATE",
                element=f"Course {course_id}",
                description=desc,
                created_at=None,
            )
        )

        return updated


def get_courses_controller(
    repository: CoursesRepository = Depends(get_courses_repository),
    audits_repository: AuditsRepository = Depends(get_audits_repository),
    users_repository: UsersRepository = Depends(get_users_repository),
):
    """Get courses controller"""

    return CoursesController(repository, audits_repository, users_repository)
