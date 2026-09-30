"""
User service module.
"""

from api.core.pagination import PaginationParams
from api.exceptions import (
    InvalidRoleError,
    PermissionDeniedError,
    ResourceAlreadyExistsError,
    ResourceNotFoundError,
    UserAlreadyExistsError,
    UserNotFoundError,
    ValidationError,
)
from api.services.audit_service import AuditService
from api.repositories.users import UsersRepository
from api.schemas.pagination import build_paginated_response
from api.schemas.user import (
    RoleName,
    UserAdminUpdate,
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
            self.users_repository.set_uid(user, current_user.uid, current_user.picture)

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
            "name": data.name,
            "active": data.active,
            "avatar_url": data.avatar_url,
            "institutional_code": data.institutional_code,
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
                contract_type=data.contract_type,
                department_id=data.department_id,
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
            "name": data.name,
            "active": data.active,
            "avatar_url": data.avatar_url,
            "institutional_code": data.institutional_code,
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

        return self._apply_update(user, data)

    async def update_user_by_id(self, user_id: int, data: UserUpdate) -> dict:
        """Same as ``update_user`` but by database id, so it also reaches a
        user who never logged in (and therefore has no uid yet)."""

        user = self.users_repository.get(user_id)

        if not user:
            raise UserNotFoundError(str(user_id))

        return self._apply_update(user, data)

    async def get_by_id(self, user_id: int) -> dict | None:
        """Retrieve user details by database id."""

        user = self.users_repository.get(user_id)

        if not user:
            return None

        return self._build_user_response(user)

    async def admin_update_user(
        self, user_id: int, data: UserAdminUpdate, current_user: dict
    ) -> dict | None:
        """Let an administrator edit name, email, institutional code, roles and
        the teacher's department of any user.

        Changing the email of a user who already logged in clears their uid:
        login looks the account up by email, so the next sign-in with the new
        address links it again and the old Firebase account loses access.
        """

        user = self.users_repository.get(user_id)

        if not user:
            return None

        payload = data.model_dump(exclude_unset=True)
        fields: dict = {}
        changes: list[str] = []

        new_email = payload.get("email")

        if new_email is not None and new_email != user.email:
            existing = self.users_repository.get_by_email(new_email)

            if existing and existing.id != user.id:
                raise UserAlreadyExistsError(new_email)

            fields["email"] = new_email
            changes.append(f"email cambió de {user.email} a {new_email}")

            if user.uid:
                fields["uid"] = None
                changes.append("se desvinculó la cuenta de Firebase")

        new_code = payload.get("institutional_code")

        if new_code is not None and new_code != user.institutional_code:
            existing = self.users_repository.get_by_institutional_code(new_code)

            if existing and existing.id != user.id:
                raise ResourceAlreadyExistsError(
                    "usuario", "código institucional", new_code
                )

            fields["institutional_code"] = new_code
            changes.append(
                f"institutional_code cambió de {user.institutional_code} a {new_code}"
            )

        new_name = payload.get("name")

        if new_name is not None and new_name != user.name:
            fields["name"] = new_name
            changes.append(f"name cambió de {user.name} a {new_name}")

        new_active = payload.get("active")

        if new_active is not None and new_active != user.active:
            fields["active"] = new_active
            changes.append(f"active cambió de {user.active} a {new_active}")

        current_roles = self.users_repository.get_user_role_names(user.id)
        final_roles = current_roles
        role_models = None

        if "roles" in payload:
            final_roles = self._normalize_role_names(payload["roles"])
            role_models = self.users_repository.get_roles_by_names(final_roles)

            if len(role_models) != len(final_roles):
                found = {r.name for r in role_models}
                raise InvalidRoleError([r for r in final_roles if r not in found])

            if (
                user.id == current_user.get("id")
                and RoleName.ADMIN.value in current_roles
                and RoleName.ADMIN.value not in final_roles
            ):
                raise ValidationError("No puedes quitarte tu propio rol ADMIN")

            if set(final_roles) != set(current_roles):
                changes.append(f"roles cambiaron de {current_roles} a {final_roles}")

        department_set = "department_id" in payload
        department_id = payload.get("department_id")

        if department_set:
            if RoleName.DOCENTE.value not in final_roles:
                raise ValidationError(
                    "El departamento solo se puede asignar a usuarios con rol DOCENTE"
                )

            if department_id is not None and not self.users_repository.department_exists(
                department_id
            ):
                raise ResourceNotFoundError("Department", department_id)

        if fields:
            self.users_repository.assign_fields(user, fields)

        if role_models is not None:
            self.users_repository.replace_user_roles(
                user.id, [r.id for r in role_models]
            )

        self._ensure_teacher(
            user,
            final_roles,
            department_id=department_id if department_set else None,
        )

        if department_set:
            teacher = self.users_repository.get_teacher_by_user_id(user.id)

            if teacher and teacher.department_id != department_id:
                changes.append(
                    f"department_id cambió de {teacher.department_id} a {department_id}"
                )
                self.users_repository.set_teacher_department(teacher, department_id)

        self.users_repository.commit()
        self.users_repository.refresh(user)

        detail = "; ".join(changes) if changes else "No se realizaron cambios"
        description = f"Se actualizó el usuario {user.email}: {detail}"

        await self.audit_service.log(
            action="UPDATE",
            entity_name="users",
            entity_id=user.id,
            actor_id=current_user.get("id"),
            description=description,
        )

        return self._build_user_response(user)

    def _apply_update(self, user, data: UserUpdate) -> dict:
        """Apply a ``UserUpdate`` (fields and/or roles) to a loaded user."""

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
        """Build a dictionary representation of the user, including roles, department and faculty info."""

        roles = self.users_repository.get_user_role_names(user.id)
        department_id = self._resolve_department_id(user, roles)
        department_name = self._resolve_department_name(department_id)
        faculty_id = self._resolve_faculty_id(user, roles)
        faculty_name = self._resolve_faculty_name(faculty_id)

        return user_to_dict(
            user,
            roles=roles,
            department_id=department_id,
            department_name=department_name,
            faculty_id=faculty_id,
            faculty_name=faculty_name,
        )

    def _resolve_department_name(self, department_id: int | None) -> str | None:
        """Resolve the department name for the given department ID."""

        if department_id is None:
            return None

        return self.users_repository.get_department_name(department_id)

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

    def _resolve_faculty_name(self, faculty_id: int | None) -> str | None:
        """Resolve the faculty name for the given faculty ID."""

        if faculty_id is None:
            return None

        return self.users_repository.get_faculty_name(faculty_id)

    def _resolve_faculty_id(self, user, roles: list[str]) -> int | None:
        """Resolve the faculty ID for the user based on their roles.

        Only a DECANO is tied to a faculty (mirrors _resolve_department_id
        for DIRECTOR DE DEPARTAMENTO/DOCENTE).
        """

        if "DECANO" in roles:
            dean = self.users_repository.get_dean_by_user_id(user.id)

            if dean:
                return dean.faculty_id
        return None

    def _ensure_teacher(
        self,
        user,
        roles: list[str],
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
