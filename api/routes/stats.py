"""
Routes for statistics operations.
"""

from typing import Annotated

from fastapi import Depends, Query

from api.controllers.stats import StatsController, get_stats_controller
from api.core.router import EnvelopeRouter
from api.middlewares.auth import get_current_user, require_roles
from api.schemas.pagination import Pagination
from api.schemas.response import ResponseSchema
from api.schemas.stats import (
    DepartmentAverageWithPreviousResponse,
    GradeDistributionResponse,
    StatsListResponse,
    SubjectListResponse,
    SubjectTeachersResponse,
    TeacherAverageWithPreviousResponse,
    TeacherCommentsBySubjectResponse,
    TeacherCoursesResponse,
    TeacherDepartmentComparisonResponse,
    TeacherDimensionAveragesResponse,
    TeacherHistoryResponse,
    TeacherMatrixResponse,
    TeacherPerformanceResponse,
    TeacherRankingListResponse,
)
from api.schemas.user import RoleName

router = EnvelopeRouter(prefix="/stats", tags=["Stats"])


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
    "/teacher-comments-by-subject",
    response_model=TeacherCommentsBySubjectResponse,
    responses={403: {"description": "Forbidden"}, 404: {"description": "Not found"}},
)
async def get_teacher_comments_by_subject(
    teacher_id: Annotated[int, Query(..., description="Teacher ID")],
    academic_period_id: Annotated[int, Query(..., description="Academic period ID")],
    _=Depends(get_current_user),
    controller: StatsController = Depends(get_stats_controller),
):
    """Endpoint to get teacher comments grouped by subject for a period."""

    result = await controller.get_teacher_comments_by_subject(
        teacher_id, academic_period_id
    )

    if result is None:
        return ResponseSchema(
            status=404,
            message="Teacher not found",
            data=None,
            path="/stats/teacher-comments-by-subject",
        )

    return ResponseSchema(
        status=200,
        message="Teacher comments by subject retrieved successfully",
        data=result,
        path="/stats/teacher-comments-by-subject",
    )


@router.get(
    "/teacher-dimension-averages",
    response_model=TeacherDimensionAveragesResponse,
    responses={403: {"description": "Forbidden"}, 404: {"description": "Not found"}},
)
async def get_teacher_dimension_averages(
    teacher_id: Annotated[int, Query(..., description="Teacher ID")],
    academic_period_id: Annotated[int, Query(..., description="Academic period ID")],
    _=Depends(get_current_user),
    controller: StatsController = Depends(get_stats_controller),
):
    """Endpoint to get teacher dimension averages for a period."""

    result = await controller.get_teacher_dimension_averages(
        teacher_id, academic_period_id
    )

    if result is None:
        return ResponseSchema(
            status=404,
            message="Teacher not found",
            data=None,
            path="/stats/teacher-dimension-averages",
        )

    return ResponseSchema(
        status=200,
        message="Teacher dimension averages retrieved successfully",
        data=result,
        path="/stats/teacher-dimension-averages",
    )


@router.get(
    "/teacher-matrix",
    response_model=TeacherMatrixResponse,
    responses={403: {"description": "Forbidden"}, 404: {"description": "Not found"}},
)
async def get_teacher_matrix(
    teacher_id: Annotated[int, Query(..., description="Teacher ID")],
    evaluation_id: Annotated[int, Query(..., description="Evaluation ID")],
    _=Depends(get_current_user),
    controller: StatsController = Depends(get_stats_controller),
):
    """Endpoint to get teacher evaluation matrix (per-course per-question averages)."""

    result = await controller.get_teacher_matrix(teacher_id, evaluation_id)

    if result is None:
        return ResponseSchema(
            status=404,
            message="Teacher not found",
            data=None,
            path="/stats/teacher-matrix",
        )

    return ResponseSchema(
        status=200,
        message="Teacher matrix retrieved successfully",
        data=result,
        path="/stats/teacher-matrix",
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
    "/teacher-vs-department",
    response_model=TeacherDepartmentComparisonResponse,
    responses={403: {"description": "Forbidden"}, 404: {"description": "Not found"}},
)
async def get_teacher_vs_department(
    teacher_id: Annotated[int, Query(..., description="Teacher ID")],
    academic_period_id: Annotated[int, Query(..., description="Academic period ID")],
    _=Depends(get_current_user),
    controller: StatsController = Depends(get_stats_controller),
):
    """Compare a teacher's per-dimension and per-question averages against the department average."""

    result = await controller.get_teacher_vs_department(teacher_id, academic_period_id)

    if result is None:
        return ResponseSchema(
            status=404,
            message="Teacher not found",
            data=None,
            path="/stats/teacher-vs-department",
        )

    return ResponseSchema(
        status=200,
        message="Teacher vs department comparison retrieved successfully",
        data=result,
        path="/stats/teacher-vs-department",
    )


@router.get(
    "/teacher-ranking",
    response_model=TeacherRankingListResponse,
    responses={403: {"description": "Forbidden"}},
)
async def get_teacher_ranking(
    academic_period_id: Annotated[int | None, Query()] = None,
    department_id: Annotated[int | None, Query()] = None,
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    search: str | None = Query(
        None, description="Search by teacher name, email or institutional code"
    ),
    sort: str = Query(
        "desc",
        description="Sort order: 'asc' for lowest average first, 'desc' for highest average first",
    ),
    _=Depends(require_roles([RoleName.ADMIN, RoleName.DIRECTOR_DE_DEPARTAMENTO])),
    controller: StatsController = Depends(get_stats_controller),
):
    """Endpoint to get paginated teacher ranking by overall average score."""

    result = await controller.get_teacher_ranking_paginated(
        academic_period_id=academic_period_id,
        department_id=department_id,
        page=page,
        limit=limit,
        search=search,
        sort=sort,
    )

    return ResponseSchema(
        status=200,
        message="Teacher ranking retrieved successfully",
        data=result["teachers"],
        pagination=Pagination(
            total=result["total"],
            page=page,
            limit=limit,
            pages=result["pages"],
        ),
        path="/stats/teacher-ranking",
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


@router.get(
    "/subjects",
    response_model=SubjectListResponse,
    responses={403: {"description": "Forbidden"}},
)
async def get_subjects(
    academic_period_id: Annotated[int, Query(..., description="Academic period ID")],
    department_id: Annotated[int | None, Query()] = None,
    _=Depends(require_roles([RoleName.ADMIN, RoleName.DIRECTOR_DE_DEPARTAMENTO])),
    controller: StatsController = Depends(get_stats_controller),
):
    """Endpoint to get subjects analytics for an academic period."""

    result = await controller.get_subjects(academic_period_id, department_id)

    return ResponseSchema(
        status=200,
        message="Subjects analytics retrieved successfully",
        data=result,
        path="/stats/subjects",
    )


@router.get(
    "/subject-teachers",
    response_model=SubjectTeachersResponse,
    responses={403: {"description": "Forbidden"}, 404: {"description": "Not found"}},
)
async def get_subject_teachers(
    course_id: Annotated[int, Query(..., description="Course ID")],
    academic_period_id: Annotated[int, Query(..., description="Academic period ID")],
    _=Depends(require_roles([RoleName.ADMIN, RoleName.DIRECTOR_DE_DEPARTAMENTO])),
    controller: StatsController = Depends(get_stats_controller),
):
    """Endpoint to get teachers for a subject with per-dimension comparison."""

    result = await controller.get_subject_teachers(course_id, academic_period_id)

    if result is None:
        return ResponseSchema(
            status=404,
            message="Course or academic period not found",
            data=None,
            path="/stats/subject-teachers",
        )

    return ResponseSchema(
        status=200,
        message="Subject teachers retrieved successfully",
        data=result,
        path="/stats/subject-teachers",
    )
