"""
Improvement plan case report model — the structured fields of Formato 1, "Casos
de docentes reportados por programas académicos a las direcciones de departamento".
"""

import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.database import Base


class ImprovementPlanCaseReportModel(Base):
    """
    Improvement plan case report model — 0..1 per plan.

    Records the complaint that originated the plan when it came from an academic
    program rather than from the evaluation scores. The received/signed PDF of
    Formato 1 is tracked separately in ``improvement_plan_documents``.
    """

    __tablename__ = "improvement_plan_case_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plan_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("improvement_plans.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    reported_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )
    # "Queja presentada"
    complaint: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # "Observaciones y anexos"
    observations: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # "Acta del Comité Curricular donde se analizó el caso"
    committee_act_reference: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )

    plan: Mapped["ImprovementPlanModel"] = relationship(
        "ImprovementPlanModel", back_populates="case_report"
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
