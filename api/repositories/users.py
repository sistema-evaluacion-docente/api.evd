"""
Users repository
"""

from typing import Annotated, Sequence

from fastapi.params import Depends
from sqlalchemy import or_
from sqlalchemy.orm import Session

from api.database import get_db
from api.models.role import RoleModel
from api.models.teacher import TeacherModel
from api.models.user import UserModel
from api.models.user_role import UserRoleModel
from api.schemas.user import RoleName, UserCreate, UserStatusUpdate, UserUpdate
from api.serializers.users import user_to_dict


class UsersRepository:
    """
    class users repository
    """

    def __init__(self, db: Session):
        self.db = db

    @staticmethod
    def _normalize_role_names(
        role_names: Sequence[RoleName | str] | None,
    ) -> list[str]:
        """Normalize role names to plain strings preserving order and uniqueness."""

        if not role_names:
            return []

        normalized: list[str] = []
        seen: set[str] = set()

        for role_name in role_names:
            value = (
                role_name.value if isinstance(role_name, RoleName) else str(role_name)
            )
            if value not in seen:
                normalized.append(value)
                seen.add(value)

        return normalized

    def _resolve_roles(self, role_names: list[str]) -> list[RoleModel]:
        """Resolve role names to RoleModel instances and validate existence."""

        if not role_names:
            return []

        roles = self.db.query(RoleModel).filter(RoleModel.name.in_(role_names)).all()

        found = {role.name for role in roles}
        missing = [role for role in role_names if role not in found]

        if missing:
            raise ValueError(f"Unknown roles: {', '.join(missing)}")

        return roles

    def _replace_user_roles(self, user_id: int, role_names: list[str]):
        """Replace all user role assignments with provided role names."""

        resolved_roles = self._resolve_roles(role_names)

        self.db.query(UserRoleModel).filter(UserRoleModel.user_id == user_id).delete()

        for role in resolved_roles:
            self.db.add(UserRoleModel(user_id=user_id, role_id=role.id))

    def _ensure_teacher(
        self,
        user: UserModel,
        roles: list[str],
        institutional_code: str | None = None,
        contract_type: str | None = None,
    ) -> None:
        """Create TeacherModel if user has DOCENTE role and no teacher record exists."""

        if RoleName.DOCENTE.value not in roles:
            return

        existing = (
            self.db.query(TeacherModel).filter(TeacherModel.user_id == user.id).first()
        )
        if existing:
            return

        teacher = TeacherModel(
            institutional_code=institutional_code or f"DOC-{user.id}",
            department_id=user.department_id,
            contract_type=contract_type,
            user_id=user.id,
            active=user.active,
        )
        self.db.add(teacher)

    def _get_user_role_names(self, user_id: int) -> list[str]:
        """Get role names for a user."""

        rows = (
            self.db.query(RoleModel.name)
            .join(UserRoleModel, UserRoleModel.role_id == RoleModel.id)
            .filter(UserRoleModel.user_id == user_id)
            .all()
        )

        return [row[0] for row in rows]

    async def save(self, data: UserCreate):
        """
        Save user and assign roles if not exists
        """

        existing_user = None
        if data.uid:
            existing_user = (
                self.db.query(UserModel).filter(UserModel.uid == data.uid).first()
            )

        if not existing_user:
            existing_user = (
                self.db.query(UserModel).filter(UserModel.email == data.email).first()
            )
            if existing_user and data.uid:
                existing_user.uid = data.uid

        normalized_roles = self._normalize_role_names(data.roles)

        if existing_user:
            if normalized_roles:
                self._replace_user_roles(existing_user.id, normalized_roles)
                self._ensure_teacher(existing_user, normalized_roles)
                self.db.commit()
            roles = self._get_user_role_names(existing_user.id)
            return user_to_dict(existing_user, roles=roles)

        user = UserModel(
            uid=data.uid,
            email=data.email,
            username=data.username,
            name=data.name,
            department_id=data.department_id,
            active=data.active,
            avatar_url=data.avatar_url,
        )

        self.db.add(user)
        self.db.flush()

        roles_to_assign = normalized_roles or [RoleName.DOCENTE.value]
        self._replace_user_roles(user.id, roles_to_assign)

        self._ensure_teacher(
            user,
            roles_to_assign,
            institutional_code=data.institutional_code,
            contract_type=data.contract_type,
        )

        self.db.commit()
        self.db.refresh(user)

        roles = self._get_user_role_names(user.id)
        return user_to_dict(user, roles=roles)

    async def get_by_uid(self, uid: str):
        """
        Get user by uid
        """

        user = self.db.query(UserModel).filter(UserModel.uid == uid).first()

        if not user:
            return None

        roles = self._get_user_role_names(user.id)
        return user_to_dict(user, roles=roles)

    async def get_by_email(self, email: str):
        """Get user by email."""

        user = self.db.query(UserModel).filter(UserModel.email == email).first()

        if not user:
            return None

        roles = self._get_user_role_names(user.id)
        return user_to_dict(user, roles=roles)

    async def get_by_username(self, username: str):
        """
        Get user by username
        """

        user = self.db.query(UserModel).filter(UserModel.username == username).first()

        if not user:
            return None

        roles = self._get_user_role_names(user.id)
        return user_to_dict(user, roles=roles)

    async def get_all(
        self,
        search: str | None = None,
        page: int = 1,
        limit: int = 10,
    ):
        """
        Get users with pagination and optional search filter
        """

        query = self.db.query(UserModel)

        if search:
            term = search.strip()
            if term:
                like_term = f"%{term}%"
                query = query.filter(
                    or_(
                        UserModel.uid.ilike(like_term),
                        UserModel.email.ilike(like_term),
                        UserModel.username.ilike(like_term),
                        UserModel.name.ilike(like_term),
                    )
                )

        total = query.count()
        pages = (total + limit - 1) // limit if total else 0
        offset = (page - 1) * limit

        users = (
            query.order_by(UserModel.created_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        if not users:
            return {
                "items": [],
                "total": total,
                "page": page,
                "limit": limit,
                "pages": pages,
            }

        user_ids = [user.id for user in users]

        role_rows = (
            self.db.query(UserRoleModel.user_id, RoleModel.name)
            .join(RoleModel, RoleModel.id == UserRoleModel.role_id)
            .filter(UserRoleModel.user_id.in_(user_ids))
            .all()
        )

        roles_by_user: dict[int, list[str]] = {}
        for user_id, role_name in role_rows:
            key = int(user_id)
            if key not in roles_by_user:
                roles_by_user[key] = []
            roles_by_user[key].append(role_name)

        return {
            "items": [
                user_to_dict(user, roles=roles_by_user.get(user.id, []))
                for user in users
            ],
            "total": total,
            "page": page,
            "limit": limit,
            "pages": pages,
        }

    async def get_by_uids(self, uids: list[str]):
        """
        Get multiple users by their uids in a single query
        """

        if not uids:
            return []

        users = self.db.query(UserModel).filter(UserModel.uid.in_(uids)).all()

        user_ids = [user.id for user in users]

        role_rows = (
            self.db.query(UserRoleModel.user_id, RoleModel.name)
            .join(RoleModel, RoleModel.id == UserRoleModel.role_id)
            .filter(UserRoleModel.user_id.in_(user_ids))
            .all()
        )

        roles_by_user: dict[int, list[str]] = {}
        for user_id, role_name in role_rows:
            key = int(user_id)
            if key not in roles_by_user:
                roles_by_user[key] = []
            roles_by_user[key].append(role_name)

        users_dict: dict[str, dict] = {
            str(user.uid): user_to_dict(user, roles=roles_by_user.get(user.id, []))
            for user in users
        }

        return [users_dict[uid] for uid in uids if uid in users_dict]

    async def get_by_ids(self, ids: list[int]):
        """Get multiple users by their database ids."""

        if not ids:
            return []

        users = self.db.query(UserModel).filter(UserModel.id.in_(ids)).all()

        user_ids = [user.id for user in users]

        role_rows = (
            self.db.query(UserRoleModel.user_id, RoleModel.name)
            .join(RoleModel, RoleModel.id == UserRoleModel.role_id)
            .filter(UserRoleModel.user_id.in_(user_ids))
            .all()
        )

        roles_by_user: dict[int, list[str]] = {}
        for user_id, role_name in role_rows:
            key = int(user_id)
            if key not in roles_by_user:
                roles_by_user[key] = []
            roles_by_user[key].append(role_name)

        users_dict: dict[int, dict] = {
            user.id: user_to_dict(user, roles=roles_by_user.get(user.id, []))
            for user in users
        }

        return [users_dict[uid] for uid in ids if uid in users_dict]

    async def update(self, uid: str, data: UserUpdate):
        """
        Update user by uid
        """

        user = self.db.query(UserModel).filter(UserModel.uid == uid).first()

        if not user:
            return None

        payload = data.model_dump(exclude_unset=True)
        requested_roles = payload.pop("roles", None)

        # update fields
        for field, value in payload.items():
            if value is not None and field != "uid":
                setattr(user, field, value)

        if requested_roles is not None:
            normalized_roles = self._normalize_role_names(requested_roles)
            self._replace_user_roles(user.id, normalized_roles)
            self._ensure_teacher(user, normalized_roles)

        self.db.commit()
        self.db.refresh(user)

        roles = self._get_user_role_names(user.id)
        return user_to_dict(user, roles=roles)

    async def update_status(self, uid: str, data: UserStatusUpdate):
        """Activate/deactivate user by uid."""

        user = self.db.query(UserModel).filter(UserModel.uid == uid).first()

        if not user:
            return None

        setattr(user, "active", data.active)

        self.db.commit()
        self.db.refresh(user)

        roles = self._get_user_role_names(user.id)
        return user_to_dict(user, roles=roles)


def get_users_repository(db: Annotated[Session, Depends(get_db)]):
    """
    Get users repository
    """

    return UsersRepository(db)
