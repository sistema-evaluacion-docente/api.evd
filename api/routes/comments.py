"""
Routes for comment operations.
"""

from api.schemas.pagination import Pagination
from fastapi import APIRouter, Depends, HTTPException, Query

from api.controllers.comments import CommentsController, get_comments_controller
from api.middlewares.auth import get_current_user, require_roles
from api.models.teacher import TeacherModel
from api.schemas.comment import (
    CommentDetailResponse,
    CommentListResponse,
    CommentPeriodListResponse,
)
from api.schemas.response import ResponseSchema
from api.schemas.user import RoleName

router = APIRouter(prefix="/comments", tags=["Comments"])


@router.get(
    "/count",
    response_model=ResponseSchema,
    responses={403: {"description": "Forbidden"}},
)
async def count_comments_by_department_and_period(
    academic_period_id: int = Query(..., description="Academic period ID"),
    risk_level: int | None = Query(None, description="Filter by risk level"),
    pedagogical_category_id: int | None = Query(
        None, description="Filter by pedagogical category ID"
    ),
    teacher_id: int | None = Query(None, description="Filter by teacher ID"),
    current_user=Depends(require_roles([RoleName.DIRECTOR_DE_DEPARTAMENTO])),
    controller: CommentsController = Depends(get_comments_controller),
):
    """Get the count of comments for the director's department and given academic period."""

    department_id = current_user.get("department_id")

    if not department_id:
        raise HTTPException(
            status_code=400,
            detail="El director no tiene un departamento asignado",
        )

    count = await controller.count_by_department_and_period(
        department_id,
        academic_period_id,
        risk_level,
        pedagogical_category_id,
        teacher_id,
    )

    return ResponseSchema(
        status=200,
        message="Comment count retrieved successfully",
        data={
            "current_count": count["current_count"],
            "previous_count": count["previous_count"],
            "department_id": department_id,
            "academic_period_id": academic_period_id,
        },
        path="/comments/count-by-department-and-period",
    )


@router.get(
    "/teacher-count",
    response_model=ResponseSchema,
    responses={403: {"description": "Forbidden"}},
)
async def count_comments_by_teacher_and_period(
    teacher_id: int = Query(..., description="Teacher ID"),
    academic_period_id: int = Query(..., description="Academic period ID"),
    current_user=Depends(get_current_user),
    controller: CommentsController = Depends(get_comments_controller),
):
    """Get the count of comments for a specific teacher in an academic period."""

    teacher = (
        controller.repository.db.query(TeacherModel)
        .filter(TeacherModel.id == teacher_id)
        .first()
    )

    if not teacher:
        raise HTTPException(
            status_code=404,
            detail="Teacher not found",
        )

    department_id = teacher.department_id

    if not department_id:
        raise HTTPException(
            status_code=400,
            detail="El docente no tiene un departamento asignado",
        )

    count = await controller.count_by_department_and_period(
        department_id,
        academic_period_id,
        None,
        None,
        teacher_id,
    )

    return ResponseSchema(
        status=200,
        message="Teacher comment count retrieved successfully",
        data={
            "current_count": count["current_count"],
            "previous_count": count["previous_count"],
            "teacher_id": teacher_id,
            "academic_period_id": academic_period_id,
        },
        path="/comments/teacher-count",
    )


@router.get(
    "/{comment_id}",
    response_model=CommentDetailResponse,
    responses={403: {"description": "Forbidden"}, 404: {"model": ResponseSchema}},
)
async def get_comment_by_id(
    comment_id: int,
    _=Depends(require_roles([RoleName.ADMIN, RoleName.DIRECTOR_DE_DEPARTAMENTO])),
    controller: CommentsController = Depends(get_comments_controller),
):
    """Endpoint to get a comment by ID."""

    comment = await controller.get_by_id(comment_id)

    if not comment:
        return ResponseSchema(
            status=404,
            message="Comment not found",
            path=f"/comments/{comment_id}",
        )

    return ResponseSchema(
        status=200,
        message="Comment found",
        data=comment,
        path=f"/comments/{comment_id}",
    )


@router.get(
    "/by-evaluation/{evaluation_id}",
    response_model=CommentListResponse,
    responses={403: {"description": "Forbidden"}},
)
async def get_comments_by_evaluation(
    evaluation_id: int,
    _=Depends(require_roles([RoleName.ADMIN, RoleName.DIRECTOR_DE_DEPARTAMENTO])),
    controller: CommentsController = Depends(get_comments_controller),
):
    """Endpoint to list all comments for a given evaluation."""

    comments = await controller.get_by_evaluation(evaluation_id)

    return ResponseSchema(
        status=200,
        message="Comments found",
        data=comments,
        path=f"/comments/by-evaluation/{evaluation_id}",
    )


@router.get(
    "/by-evaluation/{evaluation_id}/paginated",
    response_model=CommentPeriodListResponse,
    responses={403: {"description": "Forbidden"}},
)
async def get_comments_by_evaluation_paginated(
    evaluation_id: int,
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    search: str | None = Query(None, description="Search by teacher name, email or course"),
    _=Depends(require_roles([RoleName.ADMIN, RoleName.DIRECTOR_DE_DEPARTAMENTO])),
    controller: CommentsController = Depends(get_comments_controller),
):
    """Get comments for a given evaluation with pagination and search."""

    result = await controller.get_by_evaluation_paginated(
        evaluation_id,
        page=page,
        limit=limit,
        search=search,
    )

    return ResponseSchema(
        status=200,
        message="Comments retrieved successfully",
        data=result["comments"],
        pagination=Pagination(
            total=result["total"],
            page=page,
            limit=limit,
            pages=result["pages"],
        ),
        path=f"/comments/by-evaluation/{evaluation_id}/paginated",
    )


@router.get(
    "/by-teacher/{teacher_id}",
    response_model=CommentListResponse,
    responses={403: {"description": "Forbidden"}},
)
async def get_comments_by_teacher(
    teacher_id: int,
    _=Depends(require_roles([RoleName.ADMIN, RoleName.DIRECTOR_DE_DEPARTAMENTO])),
    controller: CommentsController = Depends(get_comments_controller),
):
    """Endpoint to list all comments for a given teacher."""

    comments = await controller.get_by_teacher(teacher_id)

    return ResponseSchema(
        status=200,
        message="Comments found",
        data=comments,
        path=f"/comments/by-teacher/{teacher_id}",
    )


@router.get(
    "/by-academic-group/{academic_groups_id}",
    response_model=CommentListResponse,
    responses={403: {"description": "Forbidden"}},
)
async def get_comments_by_academic_group(
    academic_groups_id: int,
    _=Depends(require_roles([RoleName.ADMIN, RoleName.DIRECTOR_DE_DEPARTAMENTO])),
    controller: CommentsController = Depends(get_comments_controller),
):
    """Endpoint to list all comments for a given academic group."""

    comments = await controller.get_by_academic_group(academic_groups_id)

    return ResponseSchema(
        status=200,
        message="Comments found",
        data=comments,
        path=f"/comments/by-academic-group/{academic_groups_id}",
    )


@router.get(
    "/by-period/{period_id}",
    response_model=CommentPeriodListResponse,
    responses={403: {"description": "Forbidden"}, 404: {"model": ResponseSchema}},
)
async def get_comments_by_period(
    period_id: int,
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(10, ge=1, le=100, description="Items per page"),
    search: str | None = Query(None, description="Search by teacher name or email"),
    risk_level: int | None = Query(None, description="Filter by risk level"),
    pedagogical_category_id: int | None = Query(
        None, description="Filter by pedagogical category ID"
    ),
    teacher_id: int | None = Query(None, description="Filter by teacher ID"),
    _=Depends(require_roles([RoleName.ADMIN, RoleName.DIRECTOR_DE_DEPARTAMENTO])),
    controller: CommentsController = Depends(get_comments_controller),
):
    """Get comments for a specific academic period with pagination and optional filters."""

    result = await controller.get_by_period(
        period_id,
        page=page,
        limit=limit,
        search=search,
        risk_level=risk_level,
        pedagogical_category_id=pedagogical_category_id,
        teacher_id=teacher_id,
    )

    if not result:
        return ResponseSchema(
            status=404,
            message="Academic period not found or no comments exist for this period",
            path=f"/comments/by-period/{period_id}",
        )

    return ResponseSchema(
        status=200,
        message="Comments retrieved successfully",
        data=result["comments"],
        pagination=Pagination(
            total=result["comment_count"],
            page=page,
            limit=limit,
            pages=result["pages"],
        ),
        path=f"/comments/by-period/{period_id}",
    )
