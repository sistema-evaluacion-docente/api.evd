"""Service for academic group-related business operations."""

from api.core.pagination import PaginationParams
from api.exceptions import ResourceAlreadyExistsError, ValidationError
from api.repositories.academic_groups import AcademicGroupsRepository
from api.repositories.academic_periods import AcademicPeriodsRepository
from api.schemas.academic_group import (
    AcademicGroupCreate,
    AcademicGroupFilters,
    AcademicGroupUpdate,
)
from api.schemas.pagination import build_paginated_response
from api.serializers.academic_groups import academic_group_to_dict
from api.services.audit_service import AuditService


class AcademicGroupService:
    """Service for academic group-related business operations."""

    def __init__(
        self,
        academic_groups_repository: AcademicGroupsRepository,
        academic_periods_repository: AcademicPeriodsRepository,
        audit_service: AuditService,
    ):
        self.academic_groups_repository = academic_groups_repository
        self.academic_periods_repository = academic_periods_repository
        self.audit_service = audit_service

    async def get_all(
        self,
        filters: AcademicGroupFilters,
        pagination: PaginationParams,
    ) -> dict:
        """Retrieve all academic groups based on filters and pagination."""

        groups, total = self.academic_groups_repository.search(filters, pagination)
        items = [self._enrich_group_to_dict(group) for group in groups]

        return build_paginated_response(items, total, pagination)

    async def get_by_id(self, group_id: int) -> dict | None:
        """Retrieve an academic group by ID."""

        group = self.academic_groups_repository.get_by_id(group_id)

        if not group:
            return None

        return self._enrich_group_to_dict(group)

    async def create(self, data: AcademicGroupCreate, current_user: dict) -> dict:
        """Create a new academic group, rejecting duplicates and inactive periods."""

        self._validate_period_active(data.academic_period_id)

        existing = self.academic_groups_repository.get_by_course_teacher_period_name(
            data.course_id,
            data.teacher_id,
            data.academic_period_id,
            data.group_name,
        )

        if existing:
            raise ResourceAlreadyExistsError(
                "academic_group",
                "course_id/teacher_id/academic_period_id/group_name",
                f"{data.course_id}/{data.teacher_id}/{data.academic_period_id}/{data.group_name}",
            )

        group = self.academic_groups_repository.create(data.model_dump())
        self.academic_groups_repository.db.commit()
        self.academic_groups_repository.db.refresh(group)

        result = self._enrich_group_to_dict(group)

        await self.audit_service.log(
            action="CREATE",
            entity_name="academic_groups",
            entity_id=group.id,
            actor_id=current_user.get("id"),
            description=(
                f"Se creó el grupo académico #{group.id} "
                f"(curso: {data.course_id}, profesor: {data.teacher_id}, "
                f"período: {data.academic_period_id}, grupo: {data.group_name})"
            ),
        )

        return result

    async def update(
        self, group_id: int, data: AcademicGroupUpdate, current_user: dict
    ) -> dict | None:
        """Update an academic group's fields."""

        group = self.academic_groups_repository.get(group_id)

        if not group:
            return None

        old_data = academic_group_to_dict(group)
        payload = data.model_dump(exclude_unset=True)

        new_period_id = payload.get("academic_period_id")

        if new_period_id is not None and new_period_id != group.academic_period_id:
            self._validate_period_active(new_period_id)

        unique_fields = (
            "course_id",
            "teacher_id",
            "academic_period_id",
            "group_name",
        )

        if any(payload.get(field) is not None for field in unique_fields):
            effective = {
                field: (
                    payload.get(field)
                    if payload.get(field) is not None
                    else getattr(group, field)
                )
                for field in unique_fields
            }

            existing = (
                self.academic_groups_repository.get_by_course_teacher_period_name(
                    effective["course_id"],
                    effective["teacher_id"],
                    effective["academic_period_id"],
                    effective["group_name"],
                    exclude_id=group_id,
                )
            )

            if existing:
                raise ResourceAlreadyExistsError(
                    "academic_group",
                    "course_id/teacher_id/academic_period_id/group_name",
                    f"{effective['course_id']}/{effective['teacher_id']}/"
                    f"{effective['academic_period_id']}/{effective['group_name']}",
                )

        updated = self.academic_groups_repository.update_group(group, payload)
        result = self._enrich_group_to_dict(updated)

        changes = []
        for field in unique_fields:
            new_val = payload.get(field)
            if new_val is not None and new_val != old_data.get(field):
                old_val = old_data.get(field)
                changes.append(f"{field} cambió de {old_val} a {new_val}")

        desc = f"Se actualizó el grupo académico #{group_id}"
        if changes:
            desc += ": " + "; ".join(changes)
        else:
            desc += ": No se realizaron cambios"

        await self.audit_service.log(
            action="UPDATE",
            entity_name="academic_groups",
            entity_id=group_id,
            actor_id=current_user.get("id"),
            description=desc,
        )

        return result

    async def delete(self, group_id: int, current_user: dict) -> dict | None:
        """Delete an academic group, rejecting if it has evaluation data."""

        group = self.academic_groups_repository.get(group_id)

        if not group:
            return None

        scores_count = self.academic_groups_repository.count_evaluation_scores(group_id)
        comments_count = self.academic_groups_repository.count_comments(group_id)

        if scores_count or comments_count:
            raise ValidationError(
                f"No se puede eliminar el grupo académico #{group_id} porque tiene "
                f"{scores_count} resultado(s) de evaluación y {comments_count} "
                "comentario(s) asociados."
            )

        old_data = academic_group_to_dict(group)
        self.academic_groups_repository.delete_group(group_id)

        await self.audit_service.log(
            action="DELETE",
            entity_name="academic_groups",
            entity_id=group_id,
            actor_id=current_user.get("id"),
            description=(
                f"Se eliminó el grupo académico #{group_id} "
                f"(curso: {old_data.get('course_id')}, "
                f"profesor: {old_data.get('teacher_id')}, "
                f"período: {old_data.get('academic_period_id')}, "
                f"grupo: {old_data.get('group_name')})"
            ),
        )

        return old_data

    def _validate_period_active(self, academic_period_id: int) -> None:
        """Validate that the academic period exists and is active."""

        period = self.academic_periods_repository.get(academic_period_id)

        if not period:
            raise ValidationError(
                f"El período académico con id '{academic_period_id}' no existe"
            )

        if not period.active:
            raise ValidationError(
                f"No se puede asignar el grupo al período '{period.code}' "
                "porque no está activo"
            )

    @staticmethod
    def _enrich_group_to_dict(group) -> dict:
        """Convert AcademicGroupModel to dict with related entities attached."""

        data = academic_group_to_dict(group)

        if group.course:
            data["course"] = {
                "id": group.course.id,
                "code": group.course.code,
                "name": group.course.name,
                "department_id": group.course.department_id,
            }

        if group.teacher:
            teacher_user = group.teacher.user
            data["teacher"] = {
                "id": group.teacher.id,
                "institutional_code": teacher_user.institutional_code if teacher_user else None,
                "name": teacher_user.name if teacher_user else None,
            }

        if group.academic_period:
            data["academic_period"] = {
                "id": group.academic_period.id,
                "code": group.academic_period.code,
                "name": group.academic_period.name,
                "active": group.academic_period.active,
            }

        return data
