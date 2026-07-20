"""Service for setting-related business operations."""

from api.core.pagination import PaginationParams
from api.exceptions import ResourceAlreadyExistsError, ResourceNotFoundError
from api.repositories.settings import SettingsRepository
from api.schemas.pagination import build_paginated_response
from api.schemas.setting import SettingCreate, SettingFilters, SettingUpdate
from api.serializers.settings import setting_history_to_dict, setting_to_dict
from api.services.audit_service import AuditService


class SettingService:
    """Service for setting-related business operations."""

    def __init__(
        self,
        settings_repository: SettingsRepository,
        audit_service: AuditService,
    ):
        self.settings_repository = settings_repository
        self.audit_service = audit_service

    async def get_all(
        self,
        filters: SettingFilters,
        pagination: PaginationParams,
    ) -> dict:
        """Retrieve all settings based on filters and pagination."""

        settings, total = self.settings_repository.search(filters, pagination)
        items = [setting_to_dict(setting) for setting in settings]

        return build_paginated_response(items, total, pagination)

    async def get_by_id(self, setting_id: int) -> dict | None:
        """Retrieve a setting by ID."""

        setting = self.settings_repository.get(setting_id)

        if not setting:
            return None

        return setting_to_dict(setting)

    async def get_by_key(self, key: str) -> dict | None:
        """Retrieve a setting by key."""

        setting = self.settings_repository.get_by_key(key)

        if not setting:
            return None

        return setting_to_dict(setting)

    async def create(self, data: SettingCreate, current_user: dict) -> dict:
        """Create a new setting, rejecting duplicate keys."""

        existing = self.settings_repository.get_by_key(data.key)

        if existing:
            raise ResourceAlreadyExistsError("setting", "key", data.key)

        setting = self.settings_repository.create_setting(data.model_dump())
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
                f"con valor {data.value} (tipo: {data.value_type})"
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

        old_value = setting.value

        payload = {"value": data.value, "changed_by": current_user.get("uid")}
        updated = self.settings_repository.update_setting(setting, payload)

        self.settings_repository.add_history(
            {
                "key": setting.key,
                "old_value": old_value,
                "new_value": data.value,
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
                f"Se actualizó la configuración {setting.key}: "
                f"valor cambió de {old_value} a {data.value}"
            ),
        )

        return result

    async def delete(self, setting_id: int, current_user: dict) -> dict | None:
        """Delete a setting."""

        setting = self.settings_repository.get(setting_id)

        if not setting:
            return None

        old_data = setting_to_dict(setting)
        self.settings_repository.delete_setting(setting_id)

        await self.audit_service.log(
            action="DELETE",
            entity_name="settings",
            entity_id=setting_id,
            actor_id=current_user.get("id"),
            description=(
                f"Se eliminó la configuración {old_data.get('key')} "
                f"con valor {old_data.get('value')}"
            ),
        )

        return old_data

    async def get_history(
        self,
        key: str | None = None,
        pagination: PaginationParams | None = None,
    ) -> dict:
        """Retrieve setting history with optional filters and pagination."""

        history, total = self.settings_repository.get_history(key, pagination)
        items = [setting_history_to_dict(h) for h in history]

        if pagination:
            return build_paginated_response(items, total, pagination)

        return {"items": items, "total": total}
