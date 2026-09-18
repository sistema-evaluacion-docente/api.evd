"""
Faculty-scope guard for DECANO.

A DECANO only sees aggregates for their own faculty, never another one's.
`department_id` (and by extension `faculty_id`) frequently arrives as a
client-supplied query param, so it is never trusted at face value — the
department's real faculty is looked up server-side and compared against
`current_user["faculty_id"]` (itself resolved server-side, never from the
token or request body).
"""

from sqlalchemy.orm import Session

from api.exceptions import PermissionDeniedError, ResourceNotFoundError
from api.models.department import DepartmentModel
from api.schemas.user import RoleName


def is_scoped_dean(current_user: dict) -> bool:
    """A DECANO is scoped to their own faculty unless they also hold a
    broader role (ADMIN/VICERRECTOR_ACADEMICO), which already sees everything."""

    roles = set(current_user.get("roles", []))

    if RoleName.ADMIN.value in roles or RoleName.VICERRECTOR_ACADEMICO.value in roles:
        return False

    return RoleName.DECANO.value in roles


def department_faculty_id(db: Session, department_id: int) -> int | None:
    """Return the `faculty_id` of a department, or raise if it doesn't exist."""

    department = db.query(DepartmentModel).filter(
        DepartmentModel.id == department_id
    ).first()

    if not department:
        raise ResourceNotFoundError("Department", department_id)

    return department.faculty_id


def assert_department_in_dean_scope(
    current_user: dict, db: Session, department_id: int
) -> None:
    """Raise 403 if a DECANO requests a department outside their faculty."""

    faculty_id = department_faculty_id(db, department_id)

    if faculty_id != current_user.get("faculty_id"):
        raise PermissionDeniedError(
            "No tienes permiso para ver información de este departamento"
        )
