"""
SQLAlchemy models package.

Import all models here to ensure they are registered with SQLAlchemy's metadata
before any relationships are resolved.
"""

from api.models.academic_group import AcademicGroupModel
from api.models.academic_period import AcademicPeriodModel
from api.models.audit import AuditModel
from api.models.comment import CommentModel
from api.models.course import CourseModel
from api.models.department import DepartmentModel
from api.models.director import DirectorsModel
from api.models.evaluation import EvaluationModel
from api.models.evaluation_question_score import EvaluationQuestionScoreModel
from api.models.evaluation_score import EvaluationScoreModel
from api.models.faculty import FacultyModel
from api.models.improvement_plan import ImprovementPlanModel
from api.models.improvement_plan_checkpoint import ImprovementPlanCheckpointModel
from api.models.improvement_plan_evidence import ImprovementPlanEvidenceModel
from api.models.improvement_plan_item import ImprovementPlanItemModel
from api.models.pedagogical_category import PedagogicalCategoryModel
from api.models.risk_level import RiskLevelModel
from api.models.role import RoleModel
from api.models.setting import SettingModel
from api.models.setting_history import SettingHistoryModel
from api.models.teacher import TeacherModel
from api.models.user import UserModel
from api.models.user_role import UserRoleModel

__all__ = [
    "AcademicGroupModel",
    "AcademicPeriodModel",
    "AuditModel",
    "CommentModel",
    "CourseModel",
    "DepartmentModel",
    "DirectorsModel",
    "EvaluationModel",
    "EvaluationQuestionScoreModel",
    "EvaluationScoreModel",
    "FacultyModel",
    "ImprovementPlanModel",
    "ImprovementPlanCheckpointModel",
    "ImprovementPlanEvidenceModel",
    "ImprovementPlanItemModel",
    "PedagogicalCategoryModel",
    "RiskLevelModel",
    "RoleModel",
    "SettingModel",
    "SettingHistoryModel",
    "TeacherModel",
    "UserModel",
    "UserRoleModel",
]
