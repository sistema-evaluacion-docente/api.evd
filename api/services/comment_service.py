"""Service for comment-related business operations."""

from api.core.pagination import PaginationParams
from api.exceptions import PermissionDeniedError, ResourceNotFoundError
from api.repositories.academic_periods import AcademicPeriodsRepository
from api.repositories.comments import CommentsRepository
from api.repositories.pedagogical_categories import PedagogicalCategoriesRepository
from api.repositories.risk_levels import RiskLevelsRepository
from api.schemas.comment import CommentFilters, CommentUpdate
from api.schemas.notification import NotificationCreate, NotificationType
from api.schemas.pagination import build_paginated_response
from api.services.audit_service import AuditService
from api.services.notification_service import NotificationService
from api.utils.plan_verification import reverify_comment

_TEXT_PREVIEW_LENGTH = 200


class CommentService:
    """Service for comment-related business operations."""

    def __init__(
        self,
        comments_repository: CommentsRepository,
        academic_periods_repository: AcademicPeriodsRepository,
        risk_levels_repository: RiskLevelsRepository,
        pedagogical_categories_repository: PedagogicalCategoriesRepository,
        audit_service: AuditService,
        notification_service: NotificationService,
    ):
        self.comments_repository = comments_repository
        self.academic_periods_repository = academic_periods_repository
        self.risk_levels_repository = risk_levels_repository
        self.pedagogical_categories_repository = pedagogical_categories_repository
        self.audit_service = audit_service
        self.notification_service = notification_service

    async def get_all(
        self,
        filters: CommentFilters,
        pagination: PaginationParams,
        department_id: int | None = None,
    ) -> dict:
        """Retrieve all comments based on filters and pagination."""

        items, total = self.comments_repository.search(
            filters, pagination, department_id
        )

        return build_paginated_response(items, total, pagination)

    async def get_by_id(self, comment_id: int) -> dict | None:
        """Retrieve a comment by ID with enriched info."""

        return self.comments_repository.get_by_id_enriched(comment_id)

    async def count_by_department_and_period(
        self,
        department_id: int,
        academic_period_id: int,
        risk_level: int | None = None,
        pedagogical_category_id: int | None = None,
        teacher_id: int | None = None,
    ) -> dict:
        """Count comments by department for current and previous academic period."""

        period = self.academic_periods_repository.get(academic_period_id)

        previous_period_id = None

        if period:
            prev_code = self.academic_periods_repository.get_previous_period_code(
                period.code
            )

            if prev_code:
                prev_period = self.academic_periods_repository.get_by_code(prev_code)

                if prev_period:
                    previous_period_id = prev_period.id

        return self.comments_repository.count_by_department_and_period(
            department_id,
            academic_period_id,
            previous_period_id,
            risk_level,
            pedagogical_category_id,
            teacher_id,
        )

    async def update_classification(
        self,
        comment_id: int,
        data: CommentUpdate,
        current_user: dict,
    ) -> dict | None:
        """Update a comment's risk_level and/or pedagogical categories.

        Only the director of the department that owns the comment's evaluation
        may perform this update. Returns None when the comment doesn't exist
        (or has no department to authorize against), which the route maps to 404.
        """

        department_id = self.comments_repository.get_department_id(comment_id)

        if department_id is None:
            return None

        if department_id != current_user.get("department_id"):
            raise PermissionDeniedError(
                "Solo el director del departamento asociado puede modificar este comentario"
            )

        if data.risk_level is not None:
            risk = await self.risk_levels_repository.get_by_id(data.risk_level)

            if not risk:
                raise ResourceNotFoundError("Nivel de riesgo", data.risk_level)

        if data.pedagogical_category_ids is not None:
            for category_id in data.pedagogical_category_ids:
                category = await self.pedagogical_categories_repository.get_by_id(
                    category_id
                )

                if not category:
                    raise ResourceNotFoundError("Categoría pedagógica", category_id)

        before = self.comments_repository.get_by_id_enriched(comment_id)

        updated = self.comments_repository.update_classification(
            comment_id,
            risk_level=data.risk_level,
            pedagogical_category_ids=data.pedagogical_category_ids,
        )

        if not updated:
            return None

        await self.audit_service.log(
            action="UPDATE",
            entity_name="comments",
            entity_id=comment_id,
            actor_id=current_user.get("id"),
            description=f"El director modificó la clasificación del comentario {comment_id}",
        )

        result = self.comments_repository.get_by_id_enriched(comment_id)

        # The plan verifications that quoted this comment copied its risk level
        # and category when they ran; re-tagging it makes those copies say
        # something the department no longer holds. Rebuilt here so the plan
        # and the comment never disagree.
        reverify_comment(self.comments_repository.db, comment_id)

        await self._notify_teacher_of_change(comment_id, before, result, current_user)

        return result

    @staticmethod
    def _diff_classification(before: dict, after: dict) -> list[str]:
        """Describe, in Spanish, what actually changed between two enriched
        comment dicts. Empty list means nothing changed."""

        changes = []

        before_risk = (before.get("risk_level") or {}).get("name")
        after_risk = (after.get("risk_level") or {}).get("name")

        if before_risk != after_risk:
            changes.append(
                f'el nivel de riesgo pasó de "{before_risk or "sin clasificar"}" '
                f'a "{after_risk or "sin clasificar"}"'
            )

        before_categories = {
            c["name"] for c in before.get("pedagogical_categories") or []
        }
        after_categories = {
            c["name"] for c in after.get("pedagogical_categories") or []
        }

        if before_categories != after_categories:
            before_label = ", ".join(sorted(before_categories)) or "ninguna"
            after_label = ", ".join(sorted(after_categories)) or "ninguna"
            changes.append(
                f'las categorías pedagógicas pasaron de "{before_label}" '
                f'a "{after_label}"'
            )

        return changes

    async def _notify_teacher_of_change(
        self,
        comment_id: int,
        before: dict | None,
        after: dict,
        current_user: dict,
    ) -> None:
        """Notify the evaluated teacher, in detail, that a director changed
        the classification of one of their comments. Best-effort: never
        blocks or fails the update."""

        if not before:
            return

        changes = self._diff_classification(before, after)

        if not changes:
            return

        teacher_user_id = self.comments_repository.get_teacher_user_id(comment_id)

        if not teacher_user_id:
            return

        preview = (after.get("original_text") or "").strip()

        if len(preview) > _TEXT_PREVIEW_LENGTH:
            preview = preview[:_TEXT_PREVIEW_LENGTH] + "..."

        message = (
            f"El director actualizó la clasificación de tu comentario en la "
            f"evaluación de {after.get('course_name') or 'un curso'} "
            f"({after.get('group_name') or 'grupo no especificado'}): "
            f"{'; '.join(changes)}. "
            f'Comentario original: "{preview}"'
        )

        await self.notification_service.create(
            NotificationCreate(
                user_id=teacher_user_id,
                title="Se actualizó la clasificación de un comentario tuyo",
                message=message,
                type=NotificationType.INFO,
                link=(
                    f"/docentes/{after['teacher_id']}"
                    if after.get("teacher_id")
                    else None
                ),
            ),
            actor_id=current_user.get("id"),
        )
