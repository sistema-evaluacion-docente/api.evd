"""
Improvement plan model (Plan de Seguimiento Docente)
"""

import datetime
from typing import Optional

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.database import Base


class ImprovementPlanModel(Base):
    """
    Improvement plan model — one plan per teacher, anchored to the period where
    the low performance was detected (origin) and the following period whose
    grades confirm compliance (verification).
    """

    __tablename__ = "improvement_plans"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True, autoincrement=True
    )
    teacher_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("teachers.id"), nullable=False, index=True
    )
    department_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("departments.id"), nullable=True
    )
    origin_period_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("academic_periods.id"), nullable=False
    )
    verification_period_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("academic_periods.id"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # BORRADOR / EN_SEGUIMIENTO / RESULTADO_DISPONIBLE /
    # CERRADO_CUMPLIDO / CERRADO_NO_CUMPLIDO / CERRADO_MANUAL
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="EN_SEGUIMIENTO"
    )
    close_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    start_date: Mapped[Optional[datetime.date]] = mapped_column(Date, nullable=True)
    end_date: Mapped[Optional[datetime.date]] = mapped_column(Date, nullable=True)
    created_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    closed_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # "PROGRAMA ACADÉMICO" of the official forms. Free text: the schema has no
    # academic programs entity.
    program_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    # "FACULTAD" / "DEPARTAMENTO ACADÉMICO" of the header table. Free text as
    # well: the director can override what the teacher record says, because the
    # printed form must match the acta even if the teacher moves department.
    # When empty the document falls back to the teacher's own faculty/department.
    faculty_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    department_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    # "ACTO ADMINISTRATIVO: ACTA No. ___ FECHA: ___" (Formato 2).
    acta_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    acta_date: Mapped[Optional[datetime.date]] = mapped_column(Date, nullable=True)
    # Acta lifecycle, independent from the plan status: BORRADOR / CERRADA /
    # FIRMADA. Once CERRADA the acta content freezes so it can be printed and
    # signed; FIRMADA is reached by uploading the signed Formato 2 back.
    acta_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="BORRADOR"
    )
    acta_closed_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    acta_closed_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    # Free-text observation blocks of the official forms.
    council_observations: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    department_director_observations: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )
    program_director_observations: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )

    items: Mapped[list["ImprovementPlanItemModel"]] = relationship(
        "ImprovementPlanItemModel",
        back_populates="plan",
        cascade="all, delete-orphan",
        order_by="ImprovementPlanItemModel.order",
    )
    checkpoints: Mapped[list["ImprovementPlanCheckpointModel"]] = relationship(
        "ImprovementPlanCheckpointModel",
        back_populates="plan",
        cascade="all, delete-orphan",
    )
    evidences: Mapped[list["ImprovementPlanEvidenceModel"]] = relationship(
        "ImprovementPlanEvidenceModel",
        back_populates="plan",
        cascade="all, delete-orphan",
        order_by="ImprovementPlanEvidenceModel.created_at",
    )
    # Asignaturas/grupos shown on the header table of Formatos 2 and 3.
    courses: Mapped[list["ImprovementPlanCourseModel"]] = relationship(
        "ImprovementPlanCourseModel",
        back_populates="plan",
        cascade="all, delete-orphan",
        order_by="ImprovementPlanCourseModel.order",
    )
    # Formato 1 (caso reportado por el programa académico), 0..1 per plan.
    case_report: Mapped[Optional["ImprovementPlanCaseReportModel"]] = relationship(
        "ImprovementPlanCaseReportModel",
        back_populates="plan",
        cascade="all, delete-orphan",
        uselist=False,
    )
    # What the following semester said about the plan, once its grades were
    # uploaded. Written after the plan is closed and never alters the closing.
    verifications: Mapped[list["ImprovementPlanVerificationModel"]] = relationship(
        "ImprovementPlanVerificationModel",
        back_populates="plan",
        cascade="all, delete-orphan",
        order_by="ImprovementPlanVerificationModel.period_id",
    )
    # Generated / signed PDFs of the three official forms.
    documents: Mapped[list["ImprovementPlanDocumentModel"]] = relationship(
        "ImprovementPlanDocumentModel",
        back_populates="plan",
        cascade="all, delete-orphan",
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
