"""Service for course-related business operations."""

from api.core.pagination import PaginationParams
from api.exceptions import PermissionDeniedError, ResourceAlreadyExistsError, ValidationError
from api.repositories.courses import CoursesRepository
from api.schemas.course import CourseCreate, CourseFilters, CourseUpdate
from api.schemas.pagination import build_paginated_response
from api.serializers.courses import course_to_dict
from api.services.audit_service import AuditService


class CourseService:
    """Service for course-related business operations.

    Every operation here is confined to the caller's own department — the
    route resolves that department from the director's token, never from a
    parameter, and hands it in. A course, or a payload, naming another
    department is refused with a 403 rather than silently answered with (or
    redirected to) the caller's own scope, the same rule ``SettingService``
    follows for settings.
    """

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
        department_id: int,
    ) -> dict:
        """Retrieve the caller's department's courses, based on filters and pagination."""

        if filters.department_id is not None and filters.department_id != department_id:
            raise PermissionDeniedError(
                "Solo puede consultar los cursos de su propio departamento"
            )

        filters.department_id = department_id

        courses, total = self.courses_repository.search(filters, pagination)
        items = [self._enrich_course_to_dict(course) for course in courses]

        return build_paginated_response(items, total, pagination)

    async def get_by_id(self, course_id: int, department_id: int) -> dict | None:
        """Retrieve a course by ID, rejecting one outside the caller's department."""

        course = self.courses_repository.get_by_id(course_id)

        if not course:
            return None

        if course.department_id != department_id:
            raise PermissionDeniedError(
                "Solo puede consultar los cursos de su propio departamento"
            )

        return self._enrich_course_to_dict(course)

    async def create(
        self, data: CourseCreate, department_id: int, current_user: dict
    ) -> dict:
        """Create a new course in the caller's department, rejecting duplicate codes."""

        if data.department_id is not None and data.department_id != department_id:
            raise PermissionDeniedError(
                "Solo puede crear cursos en su propio departamento"
            )

        existing = self.courses_repository.get_by_code(data.code)

        if existing:
            raise ResourceAlreadyExistsError("course", "code", data.code)

        payload = data.model_dump()
        payload["department_id"] = department_id

        course = self.courses_repository.create(payload)
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
                f"(nombre: {data.name}, departamento: {department_id})"
            ),
        )

        return result

    async def update(
        self,
        course_id: int,
        data: CourseUpdate,
        department_id: int,
        current_user: dict,
    ) -> dict | None:
        """Update a course's fields, rejecting one outside the caller's department."""

        course = self.courses_repository.get(course_id)

        if not course:
            return None

        if course.department_id != department_id:
            raise PermissionDeniedError(
                "Solo puede editar los cursos de su propio departamento"
            )

        old_data = course_to_dict(course)
        payload = data.model_dump(exclude_unset=True)

        if payload.get("department_id") is not None and payload["department_id"] != department_id:
            raise PermissionDeniedError(
                "Solo puede asignar cursos a su propio departamento"
            )

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

    async def update_name(
        self, course_id: int, name: str, department_id: int, current_user: dict
    ) -> dict | None:
        """Update a course's name. Restricted to courses in the director's department."""

        course = self.courses_repository.get_by_id(course_id)

        if not course:
            return None

        if course.department_id != department_id:
            raise PermissionDeniedError(
                "No tienes permiso para editar cursos de otro departamento"
            )

        old_name = course.name
        updated = self.courses_repository.update_course(course, {"name": name})
        result = self._enrich_course_to_dict(updated)

        await self.audit_service.log(
            action="UPDATE",
            entity_name="courses",
            entity_id=course_id,
            actor_id=current_user.get("id"),
            description=(
                f"Se actualizó el nombre del curso #{course_id} "
                f"({old_name} → {name})"
            ),
        )

        return result

    async def delete(
        self, course_id: int, department_id: int, current_user: dict
    ) -> dict | None:
        """Delete a course, rejecting one outside the caller's department
        or with academic groups."""

        course = self.courses_repository.get(course_id)

        if not course:
            return None

        if course.department_id != department_id:
            raise PermissionDeniedError(
                "Solo puede eliminar los cursos de su propio departamento"
            )

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
