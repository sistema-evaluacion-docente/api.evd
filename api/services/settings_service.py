"""Service for setting-related business operations."""

from api.core.pagination import PaginationParams
from api.exceptions import PermissionDeniedError, SettingAlreadyExistsError
from api.models.setting import SettingModel
from api.repositories.settings import SettingsRepository
from api.schemas.pagination import build_paginated_response
from api.schemas.setting import SettingCreate, SettingFilters, SettingUpdate
from api.schemas.user import RoleName
from api.serializers.settings import setting_history_to_dict, setting_to_dict
from api.services.audit_service import AuditService


class SettingService:
    """Service for setting-related business operations.

    Settings live in two scopes. The institutional ones (``department_id`` is
    None) are the defaults an ADMIN maintains for the whole system; every
    department can override any of them with its own value, which its director
    maintains. A director never sees or touches another department's settings,
    and can read the institutional ones but not modify them.
    """

    def __init__(
        self,
        settings_repository: SettingsRepository,
        audit_service: AuditService,
    ):
        self.settings_repository = settings_repository
        self.audit_service = audit_service

    @staticmethod
    def _is_director(current_user: dict | None) -> bool:
        """Whether the user acts as a department director and not as an ADMIN."""

        roles = set((current_user or {}).get("roles", []))

        if RoleName.ADMIN.value in roles:
            return False

        return RoleName.DIRECTOR_DE_DEPARTAMENTO.value in roles

    @staticmethod
    def _director_department_id(current_user: dict | None) -> int:
        """The department a director manages, refusing one without an assignment."""

        department_id = (current_user or {}).get("department_id")

        if not department_id:
            raise PermissionDeniedError("El director no tiene un departamento asignado")

        return department_id

    def _readable_department_id(
        self, current_user: dict | None, department_id: int | None
    ) -> int | None:
        """The department a read may cover.

        A director is pinned to its own department whatever it asked for; an
        ADMIN gets the department it asked for, or None for the institutional
        scope.
        """

        if self._is_director(current_user):
            return self._director_department_id(current_user)

        return department_id

    def _writable_department_id(
        self, current_user: dict | None, department_id: int | None
    ) -> int | None:
        """The department a write may target, rejecting anything out of reach."""

        if not self._is_director(current_user):
            return department_id

        own_department_id = self._director_department_id(current_user)

        if department_id is not None and department_id != own_department_id:
            raise PermissionDeniedError(
                "Solo puede administrar las configuraciones de su propio departamento"
            )

        return own_department_id

    def _ensure_can_manage(
        self, current_user: dict | None, setting: SettingModel
    ) -> None:
        """Reject writing an institutional setting, or another department's."""

        if not self._is_director(current_user):
            return

        own_department_id = self._director_department_id(current_user)

        if setting.department_id is None:
            raise PermissionDeniedError(
                "Las configuraciones institucionales solo las puede modificar un "
                "administrador; cree una configuración de su departamento para "
                "cambiar este valor"
            )

        if setting.department_id != own_department_id:
            raise PermissionDeniedError(
                "Solo puede administrar las configuraciones de su propio departamento"
            )

    def _ensure_can_read(
        self, current_user: dict | None, setting: SettingModel
    ) -> None:
        """A director reads the institutional settings and its department's."""

        if not self._is_director(current_user):
            return

        own_department_id = self._director_department_id(current_user)

        if setting.department_id not in (None, own_department_id):
            raise PermissionDeniedError(
                "Solo puede consultar las configuraciones de su propio departamento"
            )

    async def get_all(
        self,
        filters: SettingFilters,
        pagination: PaginationParams,
        current_user: dict | None = None,
    ) -> dict:
        """Retrieve the settings the user may see, based on filters and pagination."""

        filters.department_id = self._readable_department_id(
            current_user, filters.department_id
        )

        settings, total = self.settings_repository.search(filters, pagination)
        items = [setting_to_dict(setting) for setting in settings]

        return build_paginated_response(items, total, pagination)

    async def get_by_id(
        self, setting_id: int, current_user: dict | None = None
    ) -> dict | None:
        """Retrieve a setting by ID."""

        setting = self.settings_repository.get(setting_id)

        if not setting:
            return None

        self._ensure_can_read(current_user, setting)

        return setting_to_dict(setting)

    async def get_by_key(
        self,
        key: str,
        current_user: dict | None = None,
        department_id: int | None = None,
    ) -> dict | None:
        """Retrieve the setting that applies to the caller's department.

        The department's own value wins and the institutional one is the
        fallback, so this answers "which value is in effect for me".
        """

        resolved_department_id = self._readable_department_id(
            current_user, department_id
        )

        setting = self.settings_repository.resolve(key, resolved_department_id)

        if not setting:
            return None

        return setting_to_dict(setting)

    async def get_history(
        self,
        key: str | None = None,
        pagination: PaginationParams | None = None,
        department_id: int | None = None,
    ) -> dict:
        """Retrieve the history of one scope of a setting."""

        history, total = self.settings_repository.get_history(
            key, pagination, department_id
        )
        items = [setting_history_to_dict(h) for h in history]

        if pagination:
            return build_paginated_response(items, total, pagination)

        return {"items": items, "total": total}

    async def create(self, data: SettingCreate, current_user: dict) -> dict:
        """Create a setting, rejecting a key already taken in the same scope."""

        department_id = self._writable_department_id(current_user, data.department_id)

        existing = self.settings_repository.get_by_key(data.key, department_id)

        if existing:
            raise SettingAlreadyExistsError(
                data.key,
                existing.department.name if existing.department else None,
            )

        payload = data.model_dump()
        payload["department_id"] = department_id

        setting = self.settings_repository.create_setting(payload)
        self.settings_repository.db.commit()
        self.settings_repository.db.refresh(setting)

        result = setting_to_dict(setting)

        await self.audit_service.log(
            action="CREATE",
            entity_name="settings",
            entity_id=setting.id,
            actor_id=current_user.get("id"),
            description=(
                f"Se creó la configuración {data.key} "
                f"con valor {data.value} (tipo: {data.value_type}) "
                f"{self._scope_description(result)}"
            ),
        )

        return result

    async def update(
        self, setting_id: int, data: SettingUpdate, current_user: dict
    ) -> dict | None:
        """Update a setting's value."""

        setting = self.settings_repository.get(setting_id)

        if not setting:
            return None

        self._ensure_can_manage(current_user, setting)

        old_value = setting.value
        department_id = setting.department_id

        payload = {"value": data.value, "changed_by": current_user.get("uid")}
        updated = self.settings_repository.update_setting(setting, payload)

        self.settings_repository.add_history(
            {
                "key": setting.key,
                "old_value": old_value,
                "new_value": data.value,
                "department_id": department_id,
                "changed_by": current_user.get("uid"),
                "change_reason": data.change_reason,
            }
        )
        self.settings_repository.db.commit()

        result = setting_to_dict(updated)

        await self.audit_service.log(
            action="UPDATE",
            entity_name="settings",
            entity_id=setting_id,
            actor_id=current_user.get("id"),
            description=(
                f"Se actualizó la configuración {setting.key} "
                f"{self._scope_description(result)}: "
                f"valor cambió de {old_value} a {data.value}"
            ),
        )

        return result

    async def delete(self, setting_id: int, current_user: dict) -> dict | None:
        """Delete a setting."""

        setting = self.settings_repository.get(setting_id)

        if not setting:
            return None

        self._ensure_can_manage(current_user, setting)

        old_data = setting_to_dict(setting)
        self.settings_repository.delete_setting(setting_id)

        await self.audit_service.log(
            action="DELETE",
            entity_name="settings",
            entity_id=setting_id,
            actor_id=current_user.get("id"),
            description=(
                f"Se eliminó la configuración {old_data.get('key')} "
                f"con valor {old_data.get('value')} "
                f"{self._scope_description(old_data)}"
            ),
        )

        return old_data

    @staticmethod
    def _scope_description(setting: dict) -> str:
        """Spanish tail naming the scope a setting belongs to, for the audit log."""

        if not setting.get("department_id"):
            return "a nivel institucional"

        name = setting.get("department_name")

        return f"del departamento {name}" if name else "del departamento"
