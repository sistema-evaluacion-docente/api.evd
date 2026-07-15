"""
Routes for teacher comparison operations.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from api.controllers.comparison import (
    ComparisonController,
    get_comparison_controller,
)
from api.middlewares.auth import get_current_user
from api.schemas.comparison import TeacherSemesterComparisonResponse
from api.schemas.response import ResponseSchema

router = APIRouter(prefix="/comparison", tags=["Comparison"])


@router.get(
    "/teachers",
    response_model=TeacherSemesterComparisonResponse,
    responses={403: {"description": "Forbidden"},
               404: {"description": "Not found"}},
)
async def compare_teachers_semesters(
    current_semester: Annotated[
        int, Query(..., description="Current academic period ID")
    ],
    old_semester: Annotated[
        int, Query(..., description="Previous academic period ID to compare against")
    ],
    teacher_id: Annotated[int, Query(..., description="Teacher ID")],
    _=Depends(get_current_user),
    controller: ComparisonController = Depends(get_comparison_controller),
):
    """Compare all useful metrics for a teacher between two semesters."""

    result = await controller.compare_teachers_semesters(
        teacher_id=teacher_id,
        current_semester_id=current_semester,
        old_semester_id=old_semester,
    )

    if result is None:
        return ResponseSchema(
            status=404,
            message="Teacher not found or no data available for the specified semesters",
            data=None,
            path="/comparison/teachers",
        )

    return ResponseSchema(
        status=200,
        message="Teacher semester comparison retrieved successfully",
        data=result,
        path="/comparison/teachers",
    )
