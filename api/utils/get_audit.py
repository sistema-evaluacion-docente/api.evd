from sqlalchemy.orm import Session

from api.models.academic_group import AcademicGroupModel
from api.models.academic_period import AcademicPeriodModel
from api.models.course import CourseModel
from api.models.department import DepartmentModel
from api.models.faculty import FacultyModel
from api.models.setting import SettingModel
from api.models.teacher import TeacherModel
from api.models.user import UserModel
from api.serializers.academic_groups import academic_group_to_dict
from api.serializers.academic_periods import academic_period_to_dict
from api.serializers.courses import course_to_dict
from api.serializers.departments import department_to_dict
from api.serializers.faculties import faculty_to_dict
from api.serializers.settings import setting_to_dict
from api.serializers.teachers import teacher_to_dict
from api.serializers.users import user_to_dict


async def get_audit(element: str, db: Session):
    """
    Retrieves the audit record for a given element (table and id).
    """

    table, id = element.split(" ")

    result = None

    if table == "User":
        try:
            r = db.query(UserModel).filter(UserModel.id == int(id)).first()
        except ValueError:
            r = db.query(UserModel).filter(UserModel.uid == id).first()

        result = user_to_dict(r)
    if table == "Department":
        r = db.query(DepartmentModel).filter(DepartmentModel.id == id).first()
        result = department_to_dict(r)
    if table == "Faculty":
        r = db.query(FacultyModel).filter(FacultyModel.id == id).first()
        result = faculty_to_dict(r)
    if table == "AcademicPeriod":
        r = db.query(AcademicPeriodModel).filter(AcademicPeriodModel.id == id).first()
        result = academic_period_to_dict(r)
    if table == "Teacher":
        r = db.query(TeacherModel).filter(TeacherModel.id == id).first()
        result = teacher_to_dict(r)
    if table == "Setting":
        r = db.query(SettingModel).filter(SettingModel.id == id).first()
        result = setting_to_dict(r)
    if table == "AcademicGroup":
        r = db.query(AcademicGroupModel).filter(AcademicGroupModel.id == id).first()
        result = academic_group_to_dict(r)
    if table == "Course":
        r = db.query(CourseModel).filter(CourseModel.id == id).first()
        result = course_to_dict(r)

    return result
