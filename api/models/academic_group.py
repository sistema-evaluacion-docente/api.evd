"""
Academic group model
"""

import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.database import Base


class AcademicGroupModel(Base):
    """
    Academic group model — one row per (course, teacher, period, group_name) combination
    """

    __tablename__ = "academic_groups"
    __table_args__ = (
        UniqueConstraint(
            "course_id",
            "teacher_id",
            "academic_period_id",
            "group_name",
            name="uq_academic_groups_course_teacher_period_name",
        ),
    )

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=True)
    academic_period_id = Column(Integer, ForeignKey("academic_periods.id"), nullable=True)
    group_name = Column(String(255), nullable=True)

    course = relationship("CourseModel", back_populates="academic_groups")
    teacher = relationship("TeacherModel", back_populates="academic_groups")
    academic_period = relationship(
        "AcademicPeriodModel", back_populates="academic_groups"
    )

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=func.now(),
    )

    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=func.now(),
        onupdate=func.now(),
    )
