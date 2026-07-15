"""
Comparison controller — orchestrates teacher semester comparison logic.
"""

from fastapi.param_functions import Depends

from api.repositories.comparison import (
    ComparisonRepository,
    get_comparison_repository,
)
from api.utils.dimensions import DIMENSION_MAP, QUESTION_TEXT


class ComparisonController:
    """Controller for teacher semester comparison."""

    def __init__(self, repository: ComparisonRepository):
        self.repository = repository

    async def compare_teachers_semesters(
        self,
        teacher_id: int,
        current_semester_id: int,
        old_semester_id: int,
    ) -> dict | None:
        """
        Compare all useful metrics for a teacher between two semesters.

        Returns None if the teacher does not exist or has no data in the
        current semester.
        """

        print(current_semester_id, old_semester_id)

        teacher = await self.repository.get_teacher_info(teacher_id)
        print(teacher)
        if not teacher:
            return None

        current_period = await self.repository.get_period(current_semester_id)
        old_period = await self.repository.get_period(old_semester_id)
        print("current period", current_period)
        print("old period", old_period)
        if not current_period or not old_period:
            return None

        current_stats = await self.repository.get_overall_stats(
            teacher_id, current_semester_id
        )
        old_stats = await self.repository.get_overall_stats(
            teacher_id, old_semester_id
        )
        print(current_stats)
        if current_stats["group_count"] == 0:
            return None

        current_qs = await self.repository.get_question_averages(
            teacher_id, current_semester_id
        )
        old_qs = await self.repository.get_question_averages(
            teacher_id, old_semester_id
        )

        dimensions = self._build_dimension_comparison(current_qs, old_qs)

        current_courses_raw = await self.repository.get_courses(
            teacher_id, current_semester_id
        )
        old_courses_raw = await self.repository.get_courses(
            teacher_id, old_semester_id
        )

        current_courses = [
            {**c, "semester": current_period.code} for c in current_courses_raw
        ]
        old_courses = [
            {**c, "semester": old_period.code} for c in old_courses_raw
        ]

        current_comments_raw = await self.repository.get_comments_by_risk(
            teacher_id, current_semester_id
        )
        old_comments_raw = await self.repository.get_comments_by_risk(
            teacher_id, old_semester_id
        )

        current_comments = (
            {
                "semester": current_period.code,
                **current_comments_raw,
            }
            if current_comments_raw
            else None
        )
        old_comments = (
            {
                "semester": old_period.code,
                **old_comments_raw,
            }
            if old_comments_raw
            else None
        )

        avg_diff = None

        if (
            current_stats["overall_average"] is not None
            and old_stats["overall_average"] is not None
        ):
            avg_diff = round(
                current_stats["overall_average"] -
                old_stats["overall_average"], 2
            )

        return {
            "teacher_id": teacher["teacher_id"],
            "teacher_name": teacher["teacher_name"],
            "current_semester": current_period.code,
            "old_semester": old_period.code,
            "current_overall_average": current_stats["overall_average"],
            "old_overall_average": old_stats["overall_average"],
            "average_difference": avg_diff,
            "current_group_count": current_stats["group_count"],
            "old_group_count": old_stats["group_count"],
            "current_respondent_count": current_stats["respondent_count"],
            "old_respondent_count": old_stats["respondent_count"],
            "current_weakest_dimension": self._weakest_dimension(dimensions),
            "old_weakest_dimension": self._weakest_dimension_old(dimensions),
            "current_strongest_dimension": self._strongest_dimension(dimensions),
            "old_strongest_dimension": self._strongest_dimension_old(dimensions),
            "dimensions": dimensions,
            "current_courses": current_courses,
            "old_courses": old_courses,
            "current_comments": current_comments,
            "old_comments": old_comments,
        }

    def _build_dimension_comparison(
        self,
        current_qs: dict[str, float],
        old_qs: dict[str, float],
    ) -> list[dict]:
        """Build per-dimension and per-question comparison list."""

        dimensions = []
        for dim_name, codes in DIMENSION_MAP.items():
            questions = []
            for code in codes:
                cur = current_qs.get(code)
                old = old_qs.get(code)
                diff = round(
                    cur - old, 2) if cur is not None and old is not None else None
                questions.append(
                    {
                        "code": code,
                        "text": QUESTION_TEXT.get(code, code),
                        "current_average": cur,
                        "old_average": old,
                        "difference": diff,
                    }
                )

            cur_dim = [current_qs[c] for c in codes if c in current_qs]
            old_dim = [old_qs[c] for c in codes if c in old_qs]
            cur_avg = round(sum(cur_dim) / len(cur_dim),
                            2) if cur_dim else None
            old_avg = round(sum(old_dim) / len(old_dim),
                            2) if old_dim else None
            dim_diff = (
                round(cur_avg - old_avg, 2)
                if cur_avg is not None and old_avg is not None
                else None
            )

            dimensions.append(
                {
                    "dimension": dim_name,
                    "current_average": cur_avg,
                    "old_average": old_avg,
                    "difference": dim_diff,
                    "questions": questions,
                }
            )

        return dimensions

    @staticmethod
    def _weakest_dimension(dimensions: list[dict]) -> str | None:
        """Return the dimension with the lowest current average."""

        scored = [
            d for d in dimensions if d["current_average"] is not None
        ]
        if not scored:
            return None
        return min(scored, key=lambda d: d["current_average"])["dimension"]

    @staticmethod
    def _weakest_dimension_old(dimensions: list[dict]) -> str | None:
        """Return the dimension with the lowest old average."""

        scored = [d for d in dimensions if d["old_average"] is not None]
        if not scored:
            return None
        return min(scored, key=lambda d: d["old_average"])["dimension"]

    @staticmethod
    def _strongest_dimension(dimensions: list[dict]) -> str | None:
        """Return the dimension with the highest current average."""

        scored = [
            d for d in dimensions if d["current_average"] is not None
        ]
        if not scored:
            return None
        return max(scored, key=lambda d: d["current_average"])["dimension"]

    @staticmethod
    def _strongest_dimension_old(dimensions: list[dict]) -> str | None:
        """Return the dimension with the highest old average."""

        scored = [d for d in dimensions if d["old_average"] is not None]
        if not scored:
            return None
        return max(scored, key=lambda d: d["old_average"])["dimension"]


def get_comparison_controller(
    repository: ComparisonRepository = Depends(get_comparison_repository),
):
    """Dependency factory for ComparisonController."""

    return ComparisonController(repository)
