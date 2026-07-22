"""Seed script to create default roles, faculty, department and an admin user.

Usage:
    python scripts/seed_roles_admin.py

Required env vars for admin user:
    SEED_ADMIN_UID
    SEED_ADMIN_EMAIL

Optional env vars:
    SEED_ADMIN_NAME (default: System Admin)
    SEED_ADMIN_AVATAR_URL
    SEED_ADMIN_INSTITUTIONAL_CODE (default: 1152185)
    SEED_ADMIN_ROLES (comma-separated, default: ADMIN,DIRECTOR DE DEPARTAMENTO,DOCENTE)

Creates:
    - Roles: ADMIN, DIRECTOR DE DEPARTAMENTO, DOCENTE
    - Faculty: Ingeniería (code: ING)
    - Department: Sistemas (code: SIS)
    - Admin user with all roles
    - Teacher model linked to admin user
    - Director model linked to admin user and department
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from api.database import SessionLocal
from api.models.department import DepartmentModel
from api.models.director import DirectorsModel
from api.models.faculty import FacultyModel
from api.models.role import RoleModel
from api.models.teacher import TeacherModel
from api.models.user import UserModel
from api.models.user_role import UserRoleModel
from api.schemas.user import RoleName

_ = (DepartmentModel, DirectorsModel, FacultyModel, RoleModel, TeacherModel, UserModel, UserRoleModel)

load_dotenv()


@dataclass(frozen=True)
class DefaultRole:
    name: str
    description: str


DEFAULT_ROLES: list[DefaultRole] = [
    DefaultRole(
        name=RoleName.DOCENTE.value, description="Rol base para usuarios docentes"
    ),
    DefaultRole(
        name=RoleName.DIRECTOR_DE_DEPARTAMENTO.value,
        description="Gestion y supervision por departamento",
    ),
    DefaultRole(
        name=RoleName.ADMIN.value, description="Administracion general del sistema"
    ),
]


class SeedConfigError(ValueError):
    """Raised when mandatory seed configuration is missing."""


def parse_admin_roles() -> list[str]:
    raw_roles = os.getenv(
        "SEED_ADMIN_ROLES",
        f"{RoleName.ADMIN.value},{RoleName.DIRECTOR_DE_DEPARTAMENTO.value},{RoleName.DOCENTE.value}",
    )
    roles = [role.strip() for role in raw_roles.split(",") if role.strip()]

    if not roles:
        return [
            RoleName.ADMIN.value,
            RoleName.DIRECTOR_DE_DEPARTAMENTO.value,
            RoleName.DOCENTE.value,
        ]

    allowed = {role.value for role in RoleName}
    invalid = [role for role in roles if role not in allowed]

    if invalid:
        raise SeedConfigError(
            "Invalid roles in SEED_ADMIN_ROLES: "
            + ", ".join(invalid)
            + ". Allowed: "
            + ", ".join(sorted(allowed))
        )

    unique_roles: list[str] = []
    seen: set[str] = set()
    for role in roles:
        if role not in seen:
            unique_roles.append(role)
            seen.add(role)

    return unique_roles


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise SeedConfigError(f"Missing required env var: {name}")
    return value


def seed_roles() -> dict[str, int]:
    db = SessionLocal()
    try:
        existing_roles = db.query(RoleModel).all()
        by_name: dict[str, RoleModel] = {
            str(role.name): role for role in existing_roles
        }

        for default in DEFAULT_ROLES:
            role = by_name.get(default.name)
            if not role:
                role = RoleModel(
                    name=default.name,
                    description=default.description,
                    active=True,
                )
                db.add(role)
            else:
                (
                    db.query(RoleModel)
                    .filter(RoleModel.id == role.id)
                    .update(
                        {
                            RoleModel.description: default.description,
                            RoleModel.active: True,
                        },
                        synchronize_session=False,
                    )
                )

        db.commit()

        role_ids = {
            str(role.name): int(cast(int, role.id))
            for role in db.query(RoleModel).filter(
                RoleModel.name.in_([role.name for role in DEFAULT_ROLES])
            )
        }

        return role_ids
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def seed_faculty_and_department() -> int:
    """Create default faculty and department. Returns department ID."""
    db = SessionLocal()
    try:
        faculty = db.query(FacultyModel).filter(FacultyModel.code == "ING").first()
        if not faculty:
            faculty = FacultyModel(
                name="Ingeniería",
                code="ING",
                active=True,
            )
            db.add(faculty)
            db.flush()

        department = db.query(DepartmentModel).filter(DepartmentModel.code == "SIS").first()
        if not department:
            department = DepartmentModel(
                name="Sistemas",
                code="SIS",
                faculty_id=faculty.id,
                active=True,
            )
            db.add(department)
            db.flush()

        db.commit()
        return department.id
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def seed_admin(role_ids: dict[str, int], department_id: int) -> None:
    admin_uid = require_env("SEED_ADMIN_UID")
    admin_email = require_env("SEED_ADMIN_EMAIL")
    admin_name = os.getenv("SEED_ADMIN_NAME", "System Admin")
    admin_avatar_url = os.getenv("SEED_ADMIN_AVATAR_URL")
    admin_institutional_code = os.getenv("SEED_ADMIN_INSTITUTIONAL_CODE", "1152185")
    admin_roles = parse_admin_roles()

    db = SessionLocal()
    try:
        admin_user = db.query(UserModel).filter(UserModel.uid == admin_uid).first()

        if not admin_user:
            admin_user = UserModel(
                uid=admin_uid,
                email=admin_email,
                name=admin_name,
                active=True,
                institutional_code=admin_institutional_code,
                avatar_url=admin_avatar_url,
            )
            db.add(admin_user)
            db.flush()
        else:
            (
                db.query(UserModel)
                .filter(UserModel.uid == admin_uid)
                .update(
                    {
                        UserModel.email: admin_email,
                        UserModel.name: admin_name,
                        UserModel.active: True,
                        UserModel.avatar_url: admin_avatar_url,
                        UserModel.institutional_code: admin_institutional_code,
                    },
                    synchronize_session=False,
                )
            )

        db.query(UserRoleModel).filter(UserRoleModel.user_id == admin_user.id).delete()

        for role_name in admin_roles:
            role_id = role_ids.get(role_name)
            if role_id is None:
                raise SeedConfigError(f"Role not found in database: {role_name}")
            db.add(UserRoleModel(user_id=admin_user.id, role_id=role_id))

        if RoleName.DOCENTE.value in admin_roles:
            existing_teacher = (
                db.query(TeacherModel)
                .filter(TeacherModel.user_id == admin_user.id)
                .first()
            )
            if not existing_teacher:
                teacher = TeacherModel(
                    user_id=admin_user.id,
                    department_id=department_id,
                    active=True,
                )
                db.add(teacher)

        if RoleName.DIRECTOR_DE_DEPARTAMENTO.value in admin_roles and department_id:
            existing_director = (
                db.query(DirectorsModel)
                .filter(DirectorsModel.user_id == admin_user.id)
                .first()
            )
            if not existing_director:
                director = DirectorsModel(
                    user_id=admin_user.id,
                    department_id=department_id,
                    active=True,
                )
                db.add(director)

        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    role_ids_by_name = seed_roles()
    department_id = seed_faculty_and_department()
    seed_admin(role_ids_by_name, department_id)
    print("Seeding complete: roles, faculty, department, admin user, teacher and director models are ready.")
