"""
Repository for admin dashboard summary queries.
"""

from fastapi import Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from api.database import get_db
from api.models.academic_period import AcademicPeriodModel
from api.models.audit import AuditModel
from api.models.department import DepartmentModel
from api.models.evaluation import EvaluationModel
from api.models.faculty import FacultyModel
from api.models.teacher import TeacherModel
from api.models.user import UserModel
from api.serializers.audits import audit_to_dict


class AdminDashboardRepository:
    def __init__(self, db: Session):
        self.db = db

    async def get_counts(self) -> dict:
        """
        Get counts of various entities for the admin dashboard.
        Returns:
            dict: A dictionary containing counts of departments, faculties, users,
                  active users, teachers, evaluations, academic periods, and active periods.
        """

        departments = self.db.query(
            func.count(DepartmentModel.id)).scalar() or 0
        faculties = self.db.query(func.count(FacultyModel.id)).scalar() or 0
        users = self.db.query(func.count(UserModel.id)).scalar() or 0
        active_users = (
            self.db.query(func.count(UserModel.id))
            .filter(UserModel.active == True)
            .scalar()
            or 0
        )
        teachers = self.db.query(func.count(TeacherModel.id)).scalar() or 0
        evaluations = self.db.query(
            func.count(EvaluationModel.id)).scalar() or 0
        academic_periods = (
            self.db.query(func.count(AcademicPeriodModel.id)).scalar() or 0
        )
        active_periods = (
            self.db.query(func.count(AcademicPeriodModel.id))
            .filter(AcademicPeriodModel.active == True)
            .scalar()
            or 0
        )

        return {
            "departments": departments,
            "faculties": faculties,
            "users": users,
            "active_users": active_users,
            "teachers": teachers,
            "evaluations": evaluations,
            "academic_periods": academic_periods,
            "active_periods": active_periods,
        }

    async def get_recent_audits(self, limit: int = 10) -> list[dict]:
        """
        Get recent audits for the admin dashboard.
        """

        audits = (
            self.db.query(AuditModel).order_by(
                AuditModel.id.desc()).limit(limit).all()
        )

        return [audit_to_dict(a) for a in audits]

    async def get_recent_audits_with_users(self, limit: int = 10) -> list[dict]:
        """
        Get recent audits with associated user information for the admin dashboard.
        """

        audits = (
            self.db.query(AuditModel).order_by(
                AuditModel.id.desc()).limit(limit).all()
        )

        items = [audit_to_dict(a) for a in audits]

        user_ids = [item["user_id"] for item in items if item.get("user_id")]

        if user_ids:
            users = self.db.query(UserModel).filter(
                UserModel.id.in_(user_ids)).all()
            users_map = {u.id: u for u in users}

            for item in items:
                user = users_map.get(item.get("user_id"))
                item["user_name"] = user.name if user else None
                item["user_avatar"] = user.avatar_url if user else None

        return items

    async def get_periods(self) -> list[dict]:
        """
        Get academic periods for the admin dashboard.
        """

        periods = (
            self.db.query(AcademicPeriodModel)
            .order_by(AcademicPeriodModel.id.desc())
            .all()
        )

        return [
            {
                "id": p.id,
                "code": p.code,
                "name": p.name,
                "start_date": str(p.start_date) if p.start_date else None,
                "end_date": str(p.end_date) if p.end_date else None,
                "active": p.active or False,
            }
            for p in periods
        ]


def get_admin_dashboard_repository(
    db: Session = Depends(get_db),
):
    return AdminDashboardRepository(db)
