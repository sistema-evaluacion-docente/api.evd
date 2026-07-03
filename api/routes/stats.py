"""
Routes for statistics operations.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from api.controllers.stats import StatsController, get_stats_controller
from api.middlewares.auth import get_current_user, require_roles
from api.schemas.response import ResponseSchema
from api.schemas.stats import (
    DepartmentAverageWithPreviousResponse,
    GradeDistributionResponse,
    StatsListResponse,
    TeacherAverageWithPreviousResponse,
    TeacherCoursesResponse,
    TeacherHistoryResponse,
    TeacherPerformanceResponse,
)
from api.schemas.user import RoleName

router = APIRouter(prefix="/stats", tags=["Stats"])


@router.get(
    "/",
    response_model=StatsListResponse,
    responses={403: {"description": "Forbidden"}},
)
async def get_department_averages_by_period(
    department_id: Annotated[int | None, Query()] = None,
    _=Depends(require_roles([RoleName.ADMIN, RoleName.DIRECTOR_DE_DEPARTAMENTO])),
    controller: StatsController = Depends(get_stats_controller),
):
    """Endpoint to get global department averages by academic period."""

    stats = await controller.get_department_averages_by_period(department_id)

    return ResponseSchema(
        status=200,
        message="Department averages by period found",
        data=stats,
        path="/stats",
    )


@router.get(
    "/department-average",
    response_model=DepartmentAverageWithPreviousResponse,
    responses={403: {"description": "Forbidden"}, 404: {"description": "Not found"}},
)
async def get_department_average_with_previous(
    department_id: Annotated[int, Query(..., description="Department ID")],
    academic_period_id: Annotated[int, Query(..., description="Academic period ID")],
    _=Depends(require_roles([RoleName.ADMIN, RoleName.DIRECTOR_DE_DEPARTAMENTO])),
    controller: StatsController = Depends(get_stats_controller),
):
    """Endpoint to get department average for a period with previous period comparison."""

    result = await controller.get_department_average_with_previous(
        department_id, academic_period_id
    )

    if not result:
        return ResponseSchema(
            status=404,
            message="Department or academic period not found",
            data=None,
            path="/stats/department-average",
        )

    message = f"Department {department_id} average for period {academic_period_id} with previous period retrieved"

    return ResponseSchema(
        status=200,
        message=message,
        data=result,
        path="/stats/department-average",
    )


@router.get(
    "/teacher-average",
    response_model=TeacherAverageWithPreviousResponse,
    responses={403: {"description": "Forbidden"}, 404: {"description": "Not found"}},
)
async def get_teacher_average_with_previous(
    teacher_id: Annotated[int, Query(..., description="Teacher ID")],
    academic_period_id: Annotated[int, Query(..., description="Academic period ID")],
    _=Depends(get_current_user),
    controller: StatsController = Depends(get_stats_controller),
):
    """Endpoint to get teacher average for a period with previous period comparison."""

    result = await controller.get_teacher_average_with_previous(
        teacher_id, academic_period_id
    )

    if not result:
        return ResponseSchema(
            status=404,
            message="Teacher or academic period not found",
            data=None,
            path="/stats/teacher-average",
        )

    message = f"Teacher {teacher_id} average for period {academic_period_id} with previous period retrieved"

    return ResponseSchema(
        status=200,
        message=message,
        data=result,
        path="/stats/teacher-average",
    )


@router.get(
    "/teacher-history",
    response_model=TeacherHistoryResponse,
    responses={403: {"description": "Forbidden"}, 404: {"description": "Not found"}},
)
async def get_teacher_history(
    teacher_id: Annotated[int, Query(..., description="Teacher ID")],
    _=Depends(get_current_user),
    controller: StatsController = Depends(get_stats_controller),
):
    """Endpoint to get teacher's historical averages across all periods."""

    result = await controller.get_teacher_history(teacher_id)

    if result is None:
        return ResponseSchema(
            status=404,
            message="Teacher not found",
            data=None,
            path="/stats/teacher-history",
        )

    return ResponseSchema(
        status=200,
        message="Teacher history retrieved successfully",
        data=result,
        path="/stats/teacher-history",
    )


@router.get(
    "/teacher-courses",
    response_model=TeacherCoursesResponse,
    responses={403: {"description": "Forbidden"}, 404: {"description": "Not found"}},
)
async def get_teacher_courses(
    teacher_id: Annotated[int, Query(..., description="Teacher ID")],
    academic_period_id: Annotated[int, Query(..., description="Academic period ID")],
    _=Depends(get_current_user),
    controller: StatsController = Depends(get_stats_controller),
):
    """Endpoint to get teacher's courses with averages for a given academic period."""

    result = await controller.get_teacher_courses_by_period(
        teacher_id, academic_period_id
    )

    if result is None:
        return ResponseSchema(
            status=404,
            message="Teacher not found",
            data=None,
            path="/stats/teacher-courses",
        )

    return ResponseSchema(
        status=200,
        message="Teacher courses retrieved successfully",
        data=result,
        path="/stats/teacher-courses",
    )


@router.get(
    "/teacher-performance",
    response_model=TeacherPerformanceResponse,
    responses={403: {"description": "Forbidden"}},
)
async def get_teacher_performance_ranking(
    academic_period_id: Annotated[int | None, Query()] = None,
    _=Depends(require_roles([RoleName.ADMIN, RoleName.DIRECTOR_DE_DEPARTAMENTO])),
    controller: StatsController = Depends(get_stats_controller),
):
    """Endpoint to get top 5 and bottom 5 teachers by overall average score."""

    ranking = await controller.get_teacher_performance_ranking(academic_period_id)

    message = "Teacher performance ranking retrieved"

    if academic_period_id:
        message = (
            f"Teacher performance ranking for period {academic_period_id} retrieved"
        )

    return ResponseSchema(
        status=200,
        message=message,
        data=ranking,
        path="/stats/teacher-performance",
    )


@router.get(
    "/grade-distribution",
    response_model=GradeDistributionResponse,
    responses={403: {"description": "Forbidden"}},
)
async def get_grade_distribution(
    academic_period_id: Annotated[int | None, Query()] = None,
    department_id: Annotated[int | None, Query()] = None,
    bin_size: Annotated[float, Query(description="Histogram bin size")] = 0.5,
    _=Depends(require_roles([RoleName.ADMIN, RoleName.DIRECTOR_DE_DEPARTAMENTO])),
    controller: StatsController = Depends(get_stats_controller),
):
    """Endpoint to get grade distribution histogram for teachers."""

    distribution = await controller.get_grade_distribution(
        academic_period_id, department_id, bin_size
    )

    message = "Grade distribution retrieved"

    if academic_period_id:
        message = f"Grade distribution for period {academic_period_id} retrieved"

    return ResponseSchema(
        status=200,
        message=message,
        data=distribution,
        path="/stats/grade-distribution",
    )
