"""
Routes for comment operations.
"""

from fastapi import APIRouter, Depends, HTTPException, Query

from api.controllers.comments import CommentsController, get_comments_controller
from api.middlewares.auth import require_roles
from api.schemas.comment import CommentDetailResponse, CommentListResponse
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
        department_id, academic_period_id
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
