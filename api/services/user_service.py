"""
User service module.
"""

from api.core.pagination import PaginationParams
from api.exceptions import (
    InvalidRoleError,
    PermissionDeniedError,
    UserNotFoundError,
)
from api.services.audit_service import AuditService
from api.repositories.users import UsersRepository
from api.schemas.pagination import build_paginated_response
from api.schemas.user import (
    RoleName,
    UserCreate,
    UserFilters,
    UserRolesUpdate,
    UserStatusUpdate,
    UserUpdate,
)
from api.serializers.users import user_to_dict


class UserService:
    """Service class for user-related operations."""

    def __init__(
        self,
        users_repository: UsersRepository,
        audit_service: AuditService,
    ):
        self.users_repository = users_repository
        self.audit_service = audit_service

    async def login(self, current_user) -> dict | None:
        """Handle user login and return user details."""

        if current_user is None:
            return None

        user = self.users_repository.get_by_email(current_user.email)

        if not user:
            return None

        if not user.uid:
            self.users_repository.set_uid(user, current_user.uid)

        return self._build_user_response(user)

    async def get_by_uid(self, uid: str) -> dict | None:
        """Retrieve user details by UID."""

        user = self.users_repository.get_by_uid(uid)

        if not user:
            return None

        return self._build_user_response(user)

    async def get_all(
        self,
        filters: UserFilters,
        pagination: PaginationParams,
    ) -> dict:
        """Retrieve all users based on filters and pagination."""

        users, total = self.users_repository.search(filters, pagination)
        roles_by_user = self.users_repository.get_user_role_names_bulk(
            [u.id for u in users]
        )
        items = [
            user_to_dict(user, roles=roles_by_user.get(user.id, [])) for user in users
        ]

        return build_paginated_response(items, total, pagination)

    async def create_user(self, data: UserCreate, current_user) -> dict | None:
        """Create a new user with the provided data."""

        requester = self._get_requester(current_user)

        if not requester:
            return None

        requester_roles = requester["roles"]

        is_admin = "ADMIN" in requester_roles
        is_director = "DIRECTOR DE DEPARTAMENTO" in requester_roles

        target_roles = {
            r.value if isinstance(r, RoleName) else str(r) for r in data.roles
        }

        if is_admin:
            pass
        elif is_director:
            if target_roles - {"DOCENTE"}:
                raise PermissionDeniedError(
                    "Los directores solo pueden crear usuarios con rol DOCENTE"
                )
        else:
            raise PermissionDeniedError("No tienes permiso para crear usuarios")

        user_data = {
            "uid": data.uid,
            "email": data.email,
            "username": data.username,
            "name": data.name,
            "active": data.active,
            "avatar_url": data.avatar_url,
        }

        user, is_new = self.users_repository.find_or_create_user(user_data)

        normalized_roles = self._normalize_role_names(data.roles)

        if is_new:
            roles_to_assign = normalized_roles or [RoleName.DOCENTE.value]
            role_models = self.users_repository.get_roles_by_names(roles_to_assign)

            if len(role_models) != len(roles_to_assign):
                found = {r.name for r in role_models}
                missing = [r for r in roles_to_assign if r not in found]
                raise InvalidRoleError(missing)

            self.users_repository.replace_user_roles(
                user.id, [r.id for r in role_models]
            )
            self._ensure_teacher(
                user,
                roles_to_assign,
                institutional_code=data.institutional_code,
                contract_type=data.contract_type,
            )
        else:
            if normalized_roles:
                role_models = self.users_repository.get_roles_by_names(normalized_roles)

                if len(role_models) != len(normalized_roles):
                    found = {r.name for r in role_models}
                    missing = [r for r in normalized_roles if r not in found]
                    raise InvalidRoleError(missing)

                self.users_repository.replace_user_roles(
                    user.id, [r.id for r in role_models]
                )
                self._ensure_teacher(user, normalized_roles)

        self.users_repository.commit()
        self.users_repository.refresh(user)

        result = self._build_user_response(user)

        if is_new:
            await self.audit_service.log(
                action="CREATE",
                entity_name="users",
                entity_id=user.id,
                actor_id=requester["id"],
                description=f"Creación del usuario {data.email}",
            )

        return result

    async def create_user_with_roles(
        self,
        data: UserCreate,
        department_id: int | None = None,
    ) -> dict:
        """Create a new user with specified roles and optional department association."""

        user_data = {
            "uid": data.uid,
            "email": data.email,
            "username": data.username,
            "name": data.name,
            "active": data.active,
            "avatar_url": data.avatar_url,
        }

        user, is_new = self.users_repository.find_or_create_user(user_data)

        normalized_roles = self._normalize_role_names(data.roles) or [
            RoleName.DOCENTE.value
        ]

        if is_new:
            role_models = self.users_repository.get_roles_by_names(normalized_roles)

            self.users_repository.replace_user_roles(
                user.id, [r.id for r in role_models]
            )
            self._ensure_teacher(
                user,
                normalized_roles,
                institutional_code=data.institutional_code,
                contract_type=data.contract_type,
                department_id=department_id,
            )
        else:
            if normalized_roles:
                role_models = self.users_repository.get_roles_by_names(normalized_roles)

                self.users_repository.replace_user_roles(
                    user.id, [r.id for r in role_models]
                )
                self._ensure_teacher(user, normalized_roles)

        self.users_repository.commit()
        self.users_repository.refresh(user)

        return self._build_user_response(user)

    async def update_user(self, uid: str, data: UserUpdate) -> dict | None:
        """Update user details and roles based on provided data."""

        user = self.users_repository.get_by_uid(uid)

        if not user:
            raise UserNotFoundError(uid)

        payload = data.model_dump(exclude_unset=True)
        requested_roles = payload.pop("roles", None)

        if requested_roles is not None:
            normalized_roles = self._normalize_role_names(requested_roles)
            role_models = self.users_repository.get_roles_by_names(normalized_roles)

            if len(role_models) != len(normalized_roles):
                found = {r.name for r in role_models}
                missing = [r for r in normalized_roles if r not in found]
                raise InvalidRoleError(missing)

            self.users_repository.replace_user_roles(
                user.id, [r.id for r in role_models]
            )
            self._ensure_teacher(user, normalized_roles)

        if payload:
            self.users_repository.update_fields(user, payload)

        self.users_repository.commit()
        self.users_repository.refresh(user)

        return self._build_user_response(user)

    async def replace_roles(
        self,
        uid: str,
        payload: UserRolesUpdate,
        current_user,
    ) -> dict | None:
        """Replace the roles of a user, ensuring proper permissions."""

        requester = self._get_requester(current_user)

        if not requester:
            return None

        requester_roles = requester["roles"]

        if "ADMIN" not in requester_roles and current_user.uid != uid:
            raise PermissionDeniedError(
                "You do not have permission to replace roles for this user"
            )

        roles = list(payload.roles)
        if "ADMIN" in requester_roles:
            roles.append(RoleName.ADMIN)

        return await self.update_user(uid, UserUpdate(roles=roles))

    async def update_status(self, uid: str, data: UserStatusUpdate) -> dict | None:
        """Update the active status of a user."""

        user = self.users_repository.get_by_uid(uid)

        if not user:
            raise UserNotFoundError(uid)

        self.users_repository.update_active(user, data.active)

        return self._build_user_response(user)

    def _get_requester(self, current_user) -> dict | None:
        """Retrieve the requester user details based on the current user."""

        user = self.users_repository.get_by_uid(current_user.uid)

        if not user:
            return None

        return self._build_user_response(user)

    def _build_user_response(self, user) -> dict:
        """Build a dictionary representation of the user, including roles and department ID."""

        roles = self.users_repository.get_user_role_names(user.id)
        department_id = self._resolve_department_id(user, roles)

        return user_to_dict(user, roles=roles, department_id=department_id)

    def _resolve_department_id(self, user, roles: list[str]) -> int | None:
        """Resolve the department ID for the user based on their roles."""

        if "DIRECTOR DE DEPARTAMENTO" in roles:
            director = self.users_repository.get_director_by_user_id(user.id)

            if director:
                return director.department_id
        elif "DOCENTE" in roles:
            teacher = self.users_repository.get_teacher_by_user_id(user.id)

            if teacher:
                return teacher.department_id
        return None

    def _ensure_teacher(
        self,
        user,
        roles: list[str],
        institutional_code: str | None = None,
        contract_type: str | None = None,
        department_id: int | None = None,
    ) -> None:
        """Ensure that a user with the 'DOCENTE' role has an associated teacher record."""

        if RoleName.DOCENTE.value not in roles:
            return

        existing = self.users_repository.get_teacher_by_user_id(user.id)
        if existing:
            return

        resolved_department_id = department_id
        if resolved_department_id is None:
            director = self.users_repository.get_director_by_user_id(user.id)
            if director:
                resolved_department_id = director.department_id

        self.users_repository.create_teacher(
            user_id=user.id,
            institutional_code=institutional_code,
            contract_type=contract_type,
            department_id=resolved_department_id,
            active=user.active,
        )

    @staticmethod
    def _normalize_role_names(
        role_names,
    ) -> list[str]:
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
