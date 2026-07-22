"""Settings controller — thin delegation to SettingService."""

from fastapi.param_functions import Depends

from api.core.pagination import PaginationParams
from api.dependencies.settings import get_setting_service
from api.schemas.setting import (
    SettingCreate,
    SettingFilters,
    SettingUpdate,
)
from api.services.settings_service import SettingService


class SettingsController:
    """Controller for setting-related operations."""

    def __init__(self, service: SettingService):
        self.service = service

    async def get_all(
        self,
        filters: SettingFilters,
        pagination: PaginationParams,
    ):
        """Retrieve all settings based on filters and pagination."""

        return await self.service.get_all(filters, pagination)

    async def get_by_id(self, setting_id: int):
        """Retrieve a setting by ID."""

        return await self.service.get_by_id(setting_id)

    async def get_by_key(self, key: str):
        """Retrieve a setting by key."""

        return await self.service.get_by_key(key)

    async def create(self, data: SettingCreate, current_user: dict):
        """Create a new setting."""

        return await self.service.create(data, current_user)

    async def update(self, setting_id: int, data: SettingUpdate, current_user: dict):
        """Update a setting."""

        return await self.service.update(setting_id, data, current_user)

    async def delete(self, setting_id: int, current_user: dict):
        """Delete a setting."""

        return await self.service.delete(setting_id, current_user)

    async def get_history(
        self,
        key: str | None = None,
        pagination: PaginationParams | None = None,
    ):
        """Retrieve setting history."""

        return await self.service.get_history(key, pagination)


def get_settings_controller(
    service: SettingService = Depends(get_setting_service),
):
    """Dependency injection for SettingsController."""

    return SettingsController(service)
