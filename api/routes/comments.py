"""
Routes for comment operations.
"""

from fastapi import Depends, HTTPException, Query

from api.controllers.comments import CommentsController, get_comments_controller
from api.core.pagination import PaginationDep
from api.core.router import EnvelopeRouter
from api.middlewares.auth import get_current_user, require_roles
from api.models.teacher import TeacherModel
from api.schemas.comment import (
    CommentFiltersDep,
    CommentOut,
)
from api.schemas.response import ResponseSchema
from api.schemas.user import RoleName
from api.database import get_db
from sqlalchemy.orm import Session

router = EnvelopeRouter(prefix="/comments", tags=["Comments"])

_EVAL_ROLES = [RoleName.ADMIN, RoleName.DIRECTOR_DE_DEPARTAMENTO]


@router.get(
    "/",
    response_model=list[CommentOut],
    responses={403: {"description": "Forbidden"}},
)
async def get_all_comments(
    filters: CommentFiltersDep,
    pagination: PaginationDep,
    _=Depends(require_roles(_EVAL_ROLES)),
    controller: CommentsController = Depends(get_comments_controller),
):
    """List all comments with optional filters and pagination."""

    return await controller.get_all(filters, pagination)


@router.get(
    "/count",
    response_model=dict,
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

    return {
        "current_count": count["current_count"],
        "previous_count": count["previous_count"],
        "department_id": department_id,
        "academic_period_id": academic_period_id,
    }


@router.get(
    "/teacher-count",
    response_model=dict,
    responses={403: {"description": "Forbidden"}},
)
async def count_comments_by_teacher_and_period(
    teacher_id: int = Query(..., description="Teacher ID"),
    academic_period_id: int = Query(..., description="Academic period ID"),
    current_user=Depends(get_current_user),
    controller: CommentsController = Depends(get_comments_controller),
    db: Session = Depends(get_db),
):
    """Get the count of comments for a specific teacher in an academic period."""

    teacher = db.query(TeacherModel).filter(TeacherModel.id == teacher_id).first()

    if not teacher:
        raise HTTPException(
            status_code=404,
            detail="Docente no encontrado",
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

    return {
        "current_count": count["current_count"],
        "previous_count": count["previous_count"],
        "teacher_id": teacher_id,
        "academic_period_id": academic_period_id,
    }


@router.get(
    "/{comment_id}",
    response_model=CommentOut,
    responses={403: {"description": "Forbidden"}, 404: {"description": "Not found"}},
)
async def get_comment_by_id(
    comment_id: int,
    _=Depends(require_roles(_EVAL_ROLES)),
    controller: CommentsController = Depends(get_comments_controller),
):
    """Get a comment by ID."""

    comment = await controller.get_by_id(comment_id)

    if not comment:
        raise HTTPException(status_code=404, detail="Comentario no encontrado")

    return comment
