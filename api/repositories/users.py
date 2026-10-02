"""Repository for user-related database operations."""

from typing import Annotated

from fastapi.params import Depends
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from api.core.pagination import PaginationParams
from api.database import get_db
from api.models.dean import DeanModel
from api.models.department import DepartmentModel
from api.models.director import DirectorsModel
from api.models.faculty import FacultyModel
from api.models.role import RoleModel
from api.models.teacher import TeacherModel
from api.models.user import UserModel
from api.models.user_role import UserRoleModel
from api.repositories.base import BaseRepository
from api.schemas.user import UserFilters
from api.utils.institutional_codes import code_key


class UsersRepository(BaseRepository[UserModel]):
    """Repository for user-related database operations."""

    def __init__(self, db: Session):
        super().__init__(UserModel, db)

    def get_by_uid(self, uid: str) -> UserModel | None:
        """Retrieve a user by their unique identifier (UID)."""

        # `uid == None` compiles to `IS NULL` and would match any user that
        # never logged in.
        if not uid:
            return None

        return (
            self.db.query(UserModel)
            .options(selectinload(UserModel.teacher))
            .filter(UserModel.uid == uid)
            .first()
        )

    def get_by_email(self, email: str) -> UserModel | None:
        """Retrieve a user by their email address."""

        return self.db.query(UserModel).filter(UserModel.email == email).first()

    def get_by_institutional_codes(self, codes: list[str]) -> dict[str, UserModel]:
        """Users with any of these institutional codes, keyed by `code_key`
        (leading zeros ignored, see `api.utils.institutional_codes`), with
        their teacher record loaded in the same round trip."""

        keys = {code_key(code) for code in codes}

        if not keys:
            return {}

        users = (
            self.db.query(UserModel)
            .options(selectinload(UserModel.teacher))
            .filter(func.ltrim(UserModel.institutional_code, "0").in_(keys))
            .all()
        )

        return {code_key(user.institutional_code): user for user in users}

    def get_by_emails(self, emails: list[str]) -> dict[str, UserModel]:
        """Users with any of these emails (case-insensitive), keyed by the
        lowercased email."""

        if not emails:
            return {}

        users = (
            self.db.query(UserModel)
            .filter(func.lower(UserModel.email).in_([e.lower() for e in emails]))
            .all()
        )

        return {user.email.lower(): user for user in users}

    def get_by_institutional_code(self, code: str) -> UserModel | None:
        """Retrieve a user by their institutional code."""

        return (
            self.db.query(UserModel)
            .filter(UserModel.institutional_code == code)
            .first()
        )

    def department_exists(self, department_id: int) -> bool:
        """Check whether a department exists."""

        return (
            self.db.query(DepartmentModel.id)
            .filter(DepartmentModel.id == department_id)
            .first()
            is not None
        )

    def assign_fields(self, user: UserModel, data: dict) -> None:
        """Set user attributes without committing. Unlike ``update_fields``,
        a None value is written (e.g. clearing ``uid``)."""

        for field, value in data.items():
            setattr(user, field, value)

    def set_teacher_department(
        self, teacher: TeacherModel, department_id: int | None
    ) -> None:
        """Set a teacher's department without committing."""

        teacher.department_id = department_id

    def search(
        self,
        filters: UserFilters,
        pagination: PaginationParams,
    ) -> tuple[list[UserModel], int]:
        """Search for users based on filters and pagination parameters."""

        query = self.db.query(UserModel)

        if filters.search:
            term = filters.search.strip()

            if term:
                like_term = f"%{term}%"

                query = query.filter(
                    or_(
                        UserModel.uid.ilike(like_term),
                        UserModel.email.ilike(like_term),
                        UserModel.name.ilike(like_term),
                        UserModel.institutional_code.ilike(like_term),
                    )
                )

        if filters.department_id is not None:
            # "Belongs to the department" = teaches there or directs it. An
            # inactive director row no longer directs it, so it is left out.
            teachers_subquery = select(TeacherModel.user_id).where(
                TeacherModel.department_id == filters.department_id
            )
            directors_subquery = select(DirectorsModel.user_id).where(
                DirectorsModel.department_id == filters.department_id,
                DirectorsModel.active.isnot(False),
            )

            query = query.filter(
                or_(
                    UserModel.id.in_(teachers_subquery),
                    UserModel.id.in_(directors_subquery),
                )
            )

        if filters.active is not None:
            query = query.filter(UserModel.active == filters.active)

        if filters.roles:
            role_names = [
                role.value if hasattr(role, "value") else str(role)
                for role in filters.roles
            ]

            if role_names:
                role_subquery = (
                    select(UserRoleModel.user_id)
                    .join(RoleModel, RoleModel.id == UserRoleModel.role_id)
                    .where(RoleModel.name.in_(role_names))
                )

                query = query.filter(UserModel.id.in_(role_subquery))

        query = query.options(selectinload(UserModel.teacher)).order_by(
            UserModel.created_at.desc()
        )

        return self.paginate(query, pagination)

    def get_by_uids(self, uids: list[str]) -> list[UserModel]:
        """Retrieve users by a list of unique identifiers (UIDs)."""

        if not uids:
            return []

        return (
            self.db.query(UserModel)
            .options(selectinload(UserModel.teacher))
            .filter(UserModel.uid.in_(uids))
            .all()
        )

    def get_by_ids(self, ids: list[int]) -> list[UserModel]:
        """Retrieve users by a list of database IDs."""

        if not ids:
            return []

        return (
            self.db.query(UserModel)
            .options(selectinload(UserModel.teacher))
            .filter(UserModel.id.in_(ids))
            .all()
        )

    def get_user_role_names(self, user_id: int) -> list[str]:
        """Retrieve the names of roles associated with a specific user."""

        rows = (
            self.db.query(RoleModel.name)
            .join(UserRoleModel, UserRoleModel.role_id == RoleModel.id)
            .filter(UserRoleModel.user_id == user_id)
            .all()
        )

        return [row[0] for row in rows]

    def get_user_role_names_bulk(self, user_ids: list[int]) -> dict[int, list[str]]:
        """Retrieve the names of roles associated with multiple users."""

        if not user_ids:
            return {}

        rows = (
            self.db.query(UserRoleModel.user_id, RoleModel.name)
            .join(RoleModel, RoleModel.id == UserRoleModel.role_id)
            .filter(UserRoleModel.user_id.in_(user_ids))
            .all()
        )

        roles_by_user: dict[int, list[str]] = {}

        for user_id, role_name in rows:
            key = int(user_id)

            if key not in roles_by_user:
                roles_by_user[key] = []

            roles_by_user[key].append(role_name)

        return roles_by_user

    def get_roles_by_names(self, role_names: list[str]) -> list[RoleModel]:
        """Retrieve role models based on a list of role names."""

        if not role_names:
            return []

        return self.db.query(RoleModel).filter(RoleModel.name.in_(role_names)).all()

    def replace_user_roles(self, user_id: int, role_ids: list[int]) -> None:
        """Replace the roles associated with a specific user."""

        self.db.query(UserRoleModel).filter(UserRoleModel.user_id == user_id).delete()

        for role_id in role_ids:
            self.db.add(UserRoleModel(user_id=user_id, role_id=role_id))

    def update_fields(self, user: UserModel, data: dict) -> None:
        """Update specific fields of a user model based on provided data."""

        for field, value in data.items():
            if value is not None and field != "uid":
                setattr(user, field, value)

        self.db.commit()
        self.db.refresh(user)

    def update_active(self, user: UserModel, active: bool) -> None:
        """Update the active status of a user model."""

        user.active = active
        self.db.commit()
        self.db.refresh(user)

    def set_uid(self, user: UserModel, uid: str, picture: str | None = None) -> None:
        """Set the unique identifier (UID) for a user model."""

        user.uid = uid
        user.avatar_url = picture

        self.db.commit()

    def get_teacher_by_user_id(self, user_id: int) -> TeacherModel | None:
        """Retrieve a teacher model associated with a specific user ID."""

        return (
            self.db.query(TeacherModel).filter(TeacherModel.user_id == user_id).first()
        )

    def get_director_by_user_id(self, user_id: int) -> DirectorsModel | None:
        """Retrieve a director model associated with a specific user ID."""

        return (
            self.db.query(DirectorsModel)
            .filter(DirectorsModel.user_id == user_id)
            .first()
        )

    def get_department_name(self, department_id: int) -> str | None:
        """Retrieve the name of a department by its ID."""

        result = (
            self.db.query(DepartmentModel.name)
            .filter(DepartmentModel.id == department_id)
            .first()
        )

        return result[0] if result else None

    def get_dean_by_user_id(self, user_id: int) -> DeanModel | None:
        """Retrieve a dean model associated with a specific user ID."""

        return self.db.query(DeanModel).filter(DeanModel.user_id == user_id).first()

    def get_faculty_name(self, faculty_id: int) -> str | None:
        """Retrieve the name of a faculty by its ID."""

        result = (
            self.db.query(FacultyModel.name)
            .filter(FacultyModel.id == faculty_id)
            .first()
        )

        return result[0] if result else None

    def create_teacher(
        self,
        user_id: int,
        contract_type: str | None = None,
        department_id: int | None = None,
        active: bool | None = True,
    ) -> TeacherModel:
        """Create a new teacher model associated with a specific user ID."""

        teacher = TeacherModel(
            department_id=department_id,
            contract_type=contract_type,
            user_id=user_id,
            active=active,
        )

        self.db.add(teacher)
        self.db.flush()

        return teacher

    def find_or_create_user(self, data: dict) -> tuple[UserModel, bool]:
        """Find an existing user by UID or email, or create a new user if not found."""

        user = None
        is_new = True

        if data.get("uid"):
            user = self.db.query(UserModel).filter(UserModel.uid == data["uid"]).first()

        if not user:
            user = (
                self.db.query(UserModel)
                .filter(UserModel.email == data["email"])
                .first()
            )
            if user and data.get("uid"):
                user.uid = data["uid"]
                self.db.flush()

        if not user:
            create_fields = {
                "uid": data.get("uid"),
                "email": data["email"],
                "name": data.get("name"),
                "active": data.get("active", True),
                "avatar_url": data.get("avatar_url"),
                "institutional_code": data.get("institutional_code"),
            }
            user = UserModel(**create_fields)
            self.db.add(user)
            self.db.flush()
        else:
            is_new = False

        return user, is_new

    def commit(self) -> None:
        """Commit the current transaction to the database."""

        self.db.commit()

    def refresh(self, user: UserModel) -> None:
        """Refresh the state of a user model from the database."""

        self.db.refresh(user)


def get_users_repository(db: Annotated[Session, Depends(get_db)]):
    """Dependency injection for UsersRepository."""

    return UsersRepository(db)
