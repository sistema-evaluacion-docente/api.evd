"""Service for statistics-related business operations."""

import re

from api.core.pagination import PaginationParams
from api.exceptions import ValidationError
from api.repositories.stats import StatsRepository
from api.schemas.pagination import build_paginated_response
from api.schemas.stats import DepartmentPeriodRangeSubjectFilters

_PERIOD_CODE_PATTERN = re.compile(r"^\d{4}-[12]$")


class StatsService:
    """Service for statistics-related business operations."""

    def __init__(self, stats_repository: StatsRepository):
        self.stats_repository = stats_repository

    async def get_department_averages_by_period(
        self, department_id: int | None = None
    ) -> list[dict]:
        """Get global average per department per academic period."""

        return await self.stats_repository.get_department_averages_by_period(
            department_id
        )

    async def get_department_average_with_previous(
        self, department_id: int, academic_period_id: int
    ) -> dict | None:
        """Get department average for a period with previous period comparison."""

        return await self.stats_repository.get_department_average_with_previous(
            department_id, academic_period_id
        )

    async def get_teacher_performance_ranking(
        self, academic_period_id: int | None = None
    ) -> dict:
        """Get top 5 and bottom 5 teachers by overall average score."""

        return await self.stats_repository.get_teacher_performance_ranking(
            academic_period_id
        )

    async def get_teacher_ranking_paginated(
        self,
        academic_period_id: int | None = None,
        department_id: int | None = None,
        page: int = 1,
        limit: int = 10,
        search: str | None = None,
        sort: str = "desc",
    ) -> dict:
        """Get paginated teacher ranking by overall average score with search."""

        return await self.stats_repository.get_teacher_ranking_paginated(
            academic_period_id=academic_period_id,
            department_id=department_id,
            page=page,
            limit=limit,
            search=search,
            sort=sort,
        )

    async def get_grade_distribution(
        self,
        academic_period_id: int | None = None,
        department_id: int | None = None,
        bin_size: float = 0.5,
    ) -> dict:
        """Get grade distribution histogram for teachers."""

        return await self.stats_repository.get_grade_distribution(
            academic_period_id, department_id, bin_size
        )

    async def get_teacher_average_with_previous(
        self, teacher_id: int, academic_period_id: int
    ) -> dict | None:
        """Get teacher average for a period with previous period comparison."""

        return await self.stats_repository.get_teacher_average_with_previous(
            teacher_id, academic_period_id
        )

    async def get_teacher_history(self, teacher_id: int) -> list[dict] | None:
        """Get teacher's historical averages across all periods."""

        return await self.stats_repository.get_teacher_history(teacher_id)

    async def get_teacher_courses_by_period(
        self, teacher_id: int, academic_period_id: int
    ) -> list[dict] | None:
        """Get teacher's courses with averages for a given academic period."""

        return await self.stats_repository.get_teacher_courses_by_period(
            teacher_id, academic_period_id
        )

    async def get_teacher_comments_by_subject(
        self, teacher_id: int, academic_period_id: int
    ) -> dict | None:
        """Get teacher comments grouped by subject for a period."""

        return await self.stats_repository.get_teacher_comments_by_subject(
            teacher_id, academic_period_id
        )

    async def get_teacher_dimension_averages(
        self, teacher_id: int, academic_period_id: int
    ) -> dict | None:
        """Get teacher dimension averages for a period."""

        return await self.stats_repository.get_teacher_dimension_averages(
            teacher_id, academic_period_id
        )

    async def get_teacher_vs_department(
        self, teacher_id: int, academic_period_id: int
    ) -> dict | None:
        """Compare teacher averages per dimension and question against the department."""

        return await self.stats_repository.get_teacher_vs_department(
            teacher_id, academic_period_id
        )

    async def get_teacher_vs_previous_period(
        self, teacher_id: int, academic_period_id: int
    ) -> dict | None:
        """Compare teacher averages per dimension and question against the previous period."""

        return await self.stats_repository.get_teacher_vs_previous_period(
            teacher_id, academic_period_id
        )

    async def get_teacher_matrix(
        self, teacher_id: int, evaluation_id: int
    ) -> dict | None:
        """Get teacher evaluation matrix (per-course per-question averages)."""

        return await self.stats_repository.get_teacher_matrix(teacher_id, evaluation_id)

    async def get_subjects(
        self, academic_period_id: int, department_id: int | None = None
    ) -> list[dict]:
        """Get subjects analytics for an academic period."""

        return await self.stats_repository.get_subjects(
            academic_period_id, department_id
        )

    async def get_subject_teachers(
        self, course_id: int, academic_period_id: int
    ) -> dict | None:
        """Get teachers for a subject with per-dimension averages."""

        return await self.stats_repository.get_subject_teachers(
            course_id, academic_period_id
        )

    async def get_subject_teachers_comparison(
        self,
        department_id: int,
        course_code: str,
        period_code: str,
    ) -> list[dict]:
        """Get per-(teacher, group) comparison for a course in a period."""

        return self.stats_repository.get_subject_teachers_comparison(
            department_id, course_code, period_code
        )

    def _validate_period_range(
        self, start_period_code: str, end_period_code: str
    ) -> None:
        """Validate that both period codes are well-formed and in order."""

        if not _PERIOD_CODE_PATTERN.match(
            start_period_code
        ) or not _PERIOD_CODE_PATTERN.match(end_period_code):
            raise ValidationError(
                "El código de periodo académico debe tener el formato 'AAAA-N' "
                "(ej. '2020-1')"
            )

        if start_period_code > end_period_code:
            raise ValidationError(
                "El periodo inicial debe ser anterior o igual al periodo final"
            )

    async def get_department_period_range_report(
        self,
        department_id: int,
        start_period_code: str,
        end_period_code: str,
    ) -> dict | None:
        """
        Get a department's overall/per-period averages and pedagogical
        dimension averages aggregated across a range of academic periods.
        """

        self._validate_period_range(start_period_code, end_period_code)

        return await self.stats_repository.get_department_period_range_report(
            department_id, start_period_code, end_period_code
        )

    async def get_department_period_range_subjects(
        self,
        department_id: int,
        filters: DepartmentPeriodRangeSubjectFilters,
        pagination: PaginationParams,
    ) -> dict | None:
        """
        Get a department's subject (course) averages aggregated across a
        range of academic periods, filtered by subject name and paginated.
        """

        self._validate_period_range(filters.start_period_code, filters.end_period_code)

        result = await self.stats_repository.get_department_period_range_subjects(
            department_id, filters, pagination
        )

        if result is None:
            return None

        items, total = result

        return build_paginated_response(items, total, pagination)
