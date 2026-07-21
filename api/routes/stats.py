"""
Routes for statistics operations.
"""

from typing import Annotated

from fastapi import Depends, HTTPException, Query

from api.controllers.stats import StatsController, get_stats_controller
from api.core.router import EnvelopeRouter
from api.middlewares.auth import get_current_user, require_roles
from api.schemas.user import RoleName

router = EnvelopeRouter(prefix="/stats", tags=["Stats"])

_EVAL_ROLES = [RoleName.ADMIN, RoleName.DIRECTOR_DE_DEPARTAMENTO]


@router.get(
    "/departments/averages",
    response_model=list[dict],
    responses={403: {"description": "Forbidden"}},
)
async def get_department_averages_by_period(
    department_id: Annotated[int | None, Query()] = None,
    _=Depends(require_roles(_EVAL_ROLES)),
    controller: StatsController = Depends(get_stats_controller),
):
    """Get global department averages by academic period."""

    return await controller.get_department_averages_by_period(department_id)


@router.get(
    "/departments/{department_id}/average",
    response_model=dict,
    responses={403: {"description": "Forbidden"}, 404: {"description": "Not found"}},
)
async def get_department_average_with_previous(
    department_id: int,
    academic_period_id: Annotated[int, Query(..., description="Academic period ID")],
    _=Depends(require_roles(_EVAL_ROLES)),
    controller: StatsController = Depends(get_stats_controller),
):
    """Get department average for a period with previous period comparison."""

    result = await controller.get_department_average_with_previous(
        department_id, academic_period_id
    )

    if not result:
        raise HTTPException(
            status_code=404, detail="Departamento o periodo académico no encontrado"
        )

    return result


@router.get(
    "/teachers/{teacher_id}/average",
    response_model=dict,
    responses={403: {"description": "Forbidden"}, 404: {"description": "Not found"}},
)
async def get_teacher_average_with_previous(
    teacher_id: int,
    academic_period_id: Annotated[int, Query(..., description="Academic period ID")],
    _=Depends(get_current_user),
    controller: StatsController = Depends(get_stats_controller),
):
    """Get teacher average for a period with previous period comparison."""

    result = await controller.get_teacher_average_with_previous(
        teacher_id, academic_period_id
    )

    if not result:
        raise HTTPException(
            status_code=404, detail="Docente o periodo académico no encontrado"
        )

    return result


@router.get(
    "/teachers/{teacher_id}/history",
    response_model=list[dict],
    responses={403: {"description": "Forbidden"}, 404: {"description": "Not found"}},
)
async def get_teacher_history(
    teacher_id: int,
    _=Depends(get_current_user),
    controller: StatsController = Depends(get_stats_controller),
):
    """Get teacher's historical averages across all periods."""

    result = await controller.get_teacher_history(teacher_id)

    if result is None:
        raise HTTPException(status_code=404, detail="Docente no encontrado")

    return result


@router.get(
    "/teachers/{teacher_id}/courses",
    response_model=list[dict],
    responses={403: {"description": "Forbidden"}, 404: {"description": "Not found"}},
)
async def get_teacher_courses(
    teacher_id: int,
    academic_period_id: Annotated[int, Query(..., description="Academic period ID")],
    _=Depends(get_current_user),
    controller: StatsController = Depends(get_stats_controller),
):
    """Get teacher's courses with averages for a given academic period."""

    result = await controller.get_teacher_courses_by_period(
        teacher_id, academic_period_id
    )

    if result is None:
        raise HTTPException(status_code=404, detail="Docente no encontrado")

    return result


@router.get(
    "/teachers/{teacher_id}/comments",
    response_model=dict,
    responses={403: {"description": "Forbidden"}, 404: {"description": "Not found"}},
)
async def get_teacher_comments_by_subject(
    teacher_id: int,
    academic_period_id: Annotated[int, Query(..., description="Academic period ID")],
    _=Depends(get_current_user),
    controller: StatsController = Depends(get_stats_controller),
):
    """Get teacher comments grouped by subject for a period."""

    result = await controller.get_teacher_comments_by_subject(
        teacher_id, academic_period_id
    )

    if result is None:
        raise HTTPException(status_code=404, detail="Docente no encontrado")

    return result


@router.get(
    "/teachers/{teacher_id}/dimensions",
    response_model=dict,
    responses={403: {"description": "Forbidden"}, 404: {"description": "Not found"}},
)
async def get_teacher_dimension_averages(
    teacher_id: int,
    academic_period_id: Annotated[int, Query(..., description="Academic period ID")],
    _=Depends(get_current_user),
    controller: StatsController = Depends(get_stats_controller),
):
    """Get teacher dimension averages for a period."""

    result = await controller.get_teacher_dimension_averages(
        teacher_id, academic_period_id
    )

    if result is None:
        raise HTTPException(status_code=404, detail="Docente no encontrado")

    return result


@router.get(
    "/teachers/{teacher_id}/matrix",
    response_model=dict,
    responses={403: {"description": "Forbidden"}, 404: {"description": "Not found"}},
)
async def get_teacher_matrix(
    teacher_id: int,
    evaluation_id: Annotated[int, Query(..., description="Evaluation ID")],
    _=Depends(get_current_user),
    controller: StatsController = Depends(get_stats_controller),
):
    """Get teacher evaluation matrix (per-course per-question averages)."""

    result = await controller.get_teacher_matrix(teacher_id, evaluation_id)

    if result is None:
        raise HTTPException(status_code=404, detail="Docente no encontrado")

    return result


@router.get(
    "/teachers/ranking",
    response_model=dict,
    responses={403: {"description": "Forbidden"}},
)
async def get_teacher_performance_ranking(
    academic_period_id: Annotated[int | None, Query()] = None,
    _=Depends(require_roles(_EVAL_ROLES)),
    controller: StatsController = Depends(get_stats_controller),
):
    """Get top 5 and bottom 5 teachers by overall average score."""

    return await controller.get_teacher_performance_ranking(academic_period_id)


@router.get(
    "/teachers/ranking/paginated",
    response_model=dict,
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
    _=Depends(require_roles(_EVAL_ROLES)),
    controller: StatsController = Depends(get_stats_controller),
):
    """Get paginated teacher ranking by overall average score."""

    return await controller.get_teacher_ranking_paginated(
        academic_period_id=academic_period_id,
        department_id=department_id,
        page=page,
        limit=limit,
        search=search,
        sort=sort,
    )


@router.get(
    "/teachers/{teacher_id}/comparison",
    response_model=dict,
    responses={403: {"description": "Forbidden"}, 404: {"description": "Not found"}},
)
async def get_teacher_vs_department(
    teacher_id: int,
    academic_period_id: Annotated[int, Query(..., description="Academic period ID")],
    _=Depends(get_current_user),
    controller: StatsController = Depends(get_stats_controller),
):
    """
    Compare a teacher's per-dimension and per-question averages
    against the department average.
    """

    result = await controller.get_teacher_vs_department(teacher_id, academic_period_id)

    if result is None:
        raise HTTPException(status_code=404, detail="Docente no encontrado")

    return result


@router.get(
    "/distribution/grades",
    response_model=dict,
    responses={403: {"description": "Forbidden"}},
)
async def get_grade_distribution(
    academic_period_id: Annotated[int | None, Query()] = None,
    department_id: Annotated[int | None, Query()] = None,
    bin_size: Annotated[float, Query(description="Histogram bin size")] = 0.5,
    _=Depends(require_roles(_EVAL_ROLES)),
    controller: StatsController = Depends(get_stats_controller),
):
    """Get grade distribution histogram for teachers."""

    return await controller.get_grade_distribution(
        academic_period_id, department_id, bin_size
    )


@router.get(
    "/subjects/analytics",
    response_model=list[dict],
    responses={403: {"description": "Forbidden"}},
)
async def get_subjects(
    academic_period_id: Annotated[int, Query(..., description="Academic period ID")],
    department_id: Annotated[int | None, Query()] = None,
    _=Depends(require_roles(_EVAL_ROLES)),
    controller: StatsController = Depends(get_stats_controller),
):
    """Get subjects analytics for an academic period."""

    return await controller.get_subjects(academic_period_id, department_id)


@router.get(
    "/subjects/{course_id}/teachers",
    response_model=dict,
    responses={403: {"description": "Forbidden"}, 404: {"description": "Not found"}},
)
async def get_subject_teachers(
    course_id: int,
    academic_period_id: Annotated[int, Query(..., description="Academic period ID")],
    _=Depends(require_roles(_EVAL_ROLES)),
    controller: StatsController = Depends(get_stats_controller),
):
    """Get teachers for a subject with per-dimension comparison."""

    result = await controller.get_subject_teachers(course_id, academic_period_id)

    if result is None:
        raise HTTPException(
            status_code=404, detail="Curso o periodo académico no encontrado"
        )

    return result
