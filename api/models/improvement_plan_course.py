"""
Improvement plan course model — a row of the "ASIGNATURA / CÓDIGO / GRUPO /
PROGRAMA ACADÉMICO" table printed on Formatos 2 and 3.
"""

import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.database import Base


class ImprovementPlanCourseModel(Base):
    """
    Improvement plan course model.

    Values are a **snapshot** taken from the teacher's academic groups at plan
    creation, not a live join: the plan is an administrative document and must
    keep printing the same data even if the group is later edited or removed.
    ``academic_group_id`` is kept only as a traceability pointer.
    """

    __tablename__ = "improvement_plan_courses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plan_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("improvement_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    academic_group_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("academic_groups.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    course_name: Mapped[str] = mapped_column(String(255), nullable=False)
    course_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    group_name: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    # Per-row override of the plan-level program name. Free text: the schema has
    # no academic programs entity.
    program_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    plan: Mapped["ImprovementPlanModel"] = relationship(
        "ImprovementPlanModel", back_populates="courses"
    )

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=func.now(),
    )
