"""Service for course-related business operations."""

from api.core.pagination import PaginationParams
from api.exceptions import ResourceAlreadyExistsError, ValidationError
from api.repositories.courses import CoursesRepository
from api.schemas.course import CourseCreate, CourseFilters, CourseUpdate
from api.schemas.pagination import build_paginated_response
from api.serializers.courses import course_to_dict
from api.services.audit_service import AuditService


class CourseService:
    """Service for course-related business operations."""

    def __init__(
        self,
        courses_repository: CoursesRepository,
        audit_service: AuditService,
    ):
        self.courses_repository = courses_repository
        self.audit_service = audit_service

    async def get_all(
        self,
        filters: CourseFilters,
        pagination: PaginationParams,
    ) -> dict:
        """Retrieve all courses based on filters and pagination."""

        courses, total = self.courses_repository.search(filters, pagination)
        items = [self._enrich_course_to_dict(course) for course in courses]

        return build_paginated_response(items, total, pagination)

    async def get_by_id(self, course_id: int) -> dict | None:
        """Retrieve a course by ID."""

        course = self.courses_repository.get_by_id(course_id)

        if not course:
            return None

        return self._enrich_course_to_dict(course)

    async def create(self, data: CourseCreate, current_user: dict) -> dict:
        """Create a new course, rejecting duplicate codes."""

        existing = self.courses_repository.get_by_code(data.code)

        if existing:
            raise ResourceAlreadyExistsError("course", "code", data.code)

        course = self.courses_repository.create(data.model_dump())
        self.courses_repository.db.commit()
        self.courses_repository.db.refresh(course)

        result = self._enrich_course_to_dict(course)

        await self.audit_service.log(
            action="CREATE",
            entity_name="courses",
            entity_id=course.id,
            actor_id=current_user.get("id"),
            description=(
                f"Se creó el curso {data.code} "
                f"(nombre: {data.name}, departamento: {data.department_id})"
            ),
        )

        return result

    async def update(
        self, course_id: int, data: CourseUpdate, current_user: dict
    ) -> dict | None:
        """Update a course's fields."""

        course = self.courses_repository.get(course_id)

        if not course:
            return None

        old_data = course_to_dict(course)
        payload = data.model_dump(exclude_unset=True)

        if payload.get("code") is not None and payload.get("code") != course.code:
            existing = self.courses_repository.get_by_code(payload["code"])

            if existing and existing.id != course_id:
                raise ResourceAlreadyExistsError("course", "code", payload["code"])

        updated = self.courses_repository.update_course(course, payload)
        result = self._enrich_course_to_dict(updated)

        changes = []
        for field in ("code", "name", "department_id"):
            new_val = payload.get(field)
            if new_val is not None and new_val != old_data.get(field):
                old_val = old_data.get(field)
                changes.append(f"{field} cambió de {old_val} a {new_val}")

        desc = f"Se actualizó el curso #{course_id} ({old_data.get('name')})"
        if changes:
            desc += ": " + "; ".join(changes)
        else:
            desc += ": No se realizaron cambios"

        await self.audit_service.log(
            action="UPDATE",
            entity_name="courses",
            entity_id=course_id,
            actor_id=current_user.get("id"),
            description=desc,
        )

        return result

    async def delete(self, course_id: int, current_user: dict) -> dict | None:
        """Delete a course, rejecting if it has academic groups."""

        course = self.courses_repository.get(course_id)

        if not course:
            return None

        groups_count = self.courses_repository.count_academic_groups(course_id)

        if groups_count:
            raise ValidationError(
                f"No se puede eliminar el curso #{course_id} ({course.name}) porque tiene "
                f"{groups_count} grupo(s) académico(s) asociado(s)."
            )

        old_data = course_to_dict(course)
        self.courses_repository.delete_course(course_id)

        await self.audit_service.log(
            action="DELETE",
            entity_name="courses",
            entity_id=course_id,
            actor_id=current_user.get("id"),
            description=(
                f"Se eliminó el curso #{course_id} "
                f"(código: {old_data.get('code')}, nombre: {old_data.get('name')})"
            ),
        )

        return old_data

    @staticmethod
    def _enrich_course_to_dict(course) -> dict:
        """Convert CourseModel to dict with department summary attached."""

        data = course_to_dict(course)

        if course.department:
            data["department"] = {
                "id": course.department.id,
                "code": course.department.code,
                "name": course.department.name,
            }

        return data
