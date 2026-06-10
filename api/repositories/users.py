"""
Users repository
"""

from typing import Annotated, Sequence

from fastapi.params import Depends
from sqlalchemy.orm import Session

from api.database import get_db
from api.models.role import RoleModel
from api.models.user import UserModel
from api.models.user_role import UserRoleModel
from api.schemas.user import RoleName, UserCreate, UserUpdate
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

    def _replace_user_roles(self, user_uid: str, role_names: list[str]):
        """Replace all user role assignments with provided role names."""

        resolved_roles = self._resolve_roles(role_names)

        self.db.query(UserRoleModel).filter(UserRoleModel.user_id == user_uid).delete()

        for role in resolved_roles:
            self.db.add(UserRoleModel(user_id=user_uid, role_id=role.id))

    def _get_user_role_names(self, user_uid: str) -> list[str]:
        """Get role names for a user."""

        rows = (
            self.db.query(RoleModel.name)
            .join(UserRoleModel, UserRoleModel.role_id == RoleModel.id)
            .filter(UserRoleModel.user_id == user_uid)
            .all()
        )

        return [row[0] for row in rows]

    async def save(self, data: UserCreate):
        """
        Save user and assign roles if not exists
        """

        existing_user = (
            self.db.query(UserModel).filter(UserModel.uid == data.uid).first()
        )

        normalized_roles = self._normalize_role_names(data.roles)

        if existing_user:
            if normalized_roles:
                self._replace_user_roles(str(existing_user.uid), normalized_roles)
                self.db.commit()
            roles = self._get_user_role_names(str(existing_user.uid))
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
        self._replace_user_roles(str(user.uid), roles_to_assign)

        self.db.commit()
        self.db.refresh(user)

        roles = self._get_user_role_names(str(user.uid))
        return user_to_dict(user, roles=roles)

    async def get_by_uid(self, uid: str):
        """
        Get user by uid
        """

        user = self.db.query(UserModel).filter(UserModel.uid == uid).first()

        if not user:
            return None

        roles = self._get_user_role_names(str(user.uid))
        return user_to_dict(user, roles=roles)

    async def get_by_username(self, username: str):
        """
        Get user by username
        """

        user = self.db.query(UserModel).filter(UserModel.username == username).first()

        if not user:
            return None

        roles = self._get_user_role_names(str(user.uid))
        return user_to_dict(user, roles=roles)

    async def get_all(self):
        """
        Get all users
        """

        users = self.db.query(UserModel).order_by(UserModel.created_at.desc()).all()

        if not users:
            return []

        uids = [str(user.uid) for user in users]

        role_rows = (
            self.db.query(UserRoleModel.user_id, RoleModel.name)
            .join(RoleModel, RoleModel.id == UserRoleModel.role_id)
            .filter(UserRoleModel.user_id.in_(uids))
            .all()
        )

        roles_by_user: dict[str, list[str]] = {}
        for user_id, role_name in role_rows:
            key = str(user_id)
            if key not in roles_by_user:
                roles_by_user[key] = []
            roles_by_user[key].append(role_name)

        return [
            user_to_dict(user, roles=roles_by_user.get(str(user.uid), []))
            for user in users
        ]

    async def get_by_uids(self, uids: list[str]):
        """
        Get multiple users by their uids in a single query
        """

        if not uids:
            return []

        users = self.db.query(UserModel).filter(UserModel.uid.in_(uids)).all()

        role_rows = (
            self.db.query(UserRoleModel.user_id, RoleModel.name)
            .join(RoleModel, RoleModel.id == UserRoleModel.role_id)
            .filter(UserRoleModel.user_id.in_(uids))
            .all()
        )

        roles_by_user: dict[str, list[str]] = {}
        for user_id, role_name in role_rows:
            key = str(user_id)
            if key not in roles_by_user:
                roles_by_user[key] = []
            roles_by_user[key].append(role_name)

        users_dict: dict[str, dict] = {
            str(user.uid): user_to_dict(
                user, roles=roles_by_user.get(str(user.uid), [])
            )
            for user in users
        }

        return [users_dict[uid] for uid in uids if uid in users_dict]

    async def update(self, uid: str, data: UserUpdate):
        """
        Update user by uid
        """

        user = self.db.query(UserModel).filter(UserModel.uid == uid).first()

        if not user:
            return None

        if uid != user.uid:
            raise ValueError("Only the owner can update their profile")

        payload = data.model_dump(exclude_unset=True)
        requested_roles = payload.pop("roles", None)

        # update fields
        for field, value in payload.items():
            if value is not None and field != "uid":
                setattr(user, field, value)

        if requested_roles is not None:
            normalized_roles = self._normalize_role_names(requested_roles)
            self._replace_user_roles(str(user.uid), normalized_roles)

        self.db.commit()
        self.db.refresh(user)

        roles = self._get_user_role_names(str(user.uid))
        return user_to_dict(user, roles=roles)


def get_users_repository(db: Annotated[Session, Depends(get_db)]):
    """
    Get users repository
    """

    return UsersRepository(db)
