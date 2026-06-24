"""
Settings controller
"""

from fastapi.param_functions import Depends

from api.repositories.audits import AuditsRepository, get_audits_repository
from api.repositories.settings import (
    SettingsRepository,
    get_settings_repository,
)
from api.schemas.audit import AuditCreate
from api.schemas.setting import SettingCreate, SettingUpdate


class SettingsController:
    def __init__(
        self,
        repository: SettingsRepository,
        audits_repository: AuditsRepository,
    ):
        self.repository = repository
        self.audits_repository = audits_repository

    async def create(self, data: SettingCreate, current_user) -> dict | None:
        existing = await self.repository.get_by_key(data.key)

        if existing:
            raise ValueError(f"A setting with key '{data.key}' already exists")

        setting = await self.repository.create(data)

        await self.audits_repository.create(
            AuditCreate(
                user_id=current_user.uid,
                table_name="settings",
                operation="create",
                element=f"Setting {setting.get('id')}",
                description=f"Se creó la configuración {data.key} con valor {data.value} (tipo: {data.value_type})",
                created_at=None,
            )
        )

        return setting

    async def get_all(
        self,
        search: str | None = None,
        page: int = 1,
        limit: int = 10,
    ) -> dict | None:
        try:
            return await self.repository.get_all(search=search, page=page, limit=limit)
        except ValueError as e:
            print(e)
            return None

    async def get_by_id(self, setting_id: int) -> dict | None:
        return await self.repository.get_by_id(setting_id)

    async def get_by_key(self, key: str) -> dict | None:
        return await self.repository.get_by_key(key)

    async def update(
        self, setting_id: int, data: SettingUpdate, current_user
    ) -> dict | None:
        setting = await self.repository.get_by_id(setting_id)

        if not setting:
            return None

        result = await self.repository.update(
            setting_id, data, changed_by=current_user.uid
        )

        await self.repository.add_history(
            key=setting["key"],
            old_value=result["old_value"],
            new_value=data.value,
            changed_by=current_user.uid,
            change_reason=data.change_reason,
        )

        await self.audits_repository.create(
            AuditCreate(
                user_id=current_user.uid,
                table_name="settings",
                operation="update",
                element=f"Setting {setting_id}",
                description=f"Se actualizó la configuración {setting.get('key')}: valor cambió de {setting.get('value')} a {data.value}",
                created_at=None,
            )
        )

        return result["setting"]

    async def delete(self, setting_id: int, current_user) -> dict | None:
        setting = await self.repository.get_by_id(setting_id)

        if not setting:
            return None

        deleted = await self.repository.delete(setting_id)

        await self.audits_repository.create(
            AuditCreate(
                user_id=current_user.uid,
                table_name="settings",
                operation="delete",
                element=f"Setting {setting_id}",
                description=f"Se eliminó la configuración {setting.get('key')} con valor {setting.get('value')}",
                created_at=None,
            )
        )

        return deleted

    async def get_history(
        self,
        setting_id: int | None = None,
        key: str | None = None,
        page: int = 1,
        limit: int = 10,
    ) -> dict | None:
        try:
            return await self.repository.get_history(
                setting_id=setting_id, key=key, page=page, limit=limit
            )
        except ValueError as e:
            print(e)
            return None


def get_settings_controller(
    repository: SettingsRepository = Depends(get_settings_repository),
    audits_repository: AuditsRepository = Depends(get_audits_repository),
):
    return SettingsController(repository, audits_repository)
