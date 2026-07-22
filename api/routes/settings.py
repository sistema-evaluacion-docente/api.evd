"""Routes for setting operations."""

from fastapi import Depends, HTTPException

from api.controllers.settings import (
    SettingsController,
    get_settings_controller,
)
from api.core.pagination import PaginationDep
from api.core.router import EnvelopeRouter
from api.middlewares.auth import require_roles
from api.schemas.setting import (
    SettingCreate,
    SettingFiltersDep,
    SettingHistoryOut,
    SettingOut,
    SettingUpdate,
)
from api.schemas.user import RoleName

router = EnvelopeRouter(prefix="/settings", tags=["Settings"])

_ROLES = [RoleName.ADMIN]


@router.get("/", response_model=list[SettingOut])
async def get_all_settings(
    filters: SettingFiltersDep,
    pagination: PaginationDep,
    _=Depends(require_roles(_ROLES)),
    controller: SettingsController = Depends(get_settings_controller),
):
    """List all settings with pagination and filters."""

    return await controller.get_all(filters, pagination)


@router.get("/by-key/{key}", response_model=SettingOut)
async def get_setting_by_key(
    key: str,
    _=Depends(require_roles(_ROLES)),
    controller: SettingsController = Depends(get_settings_controller),
):
    """Get a setting by key."""

    setting = await controller.get_by_key(key)

    if not setting:
        raise HTTPException(status_code=404, detail="Configuración no encontrada")

    return setting


@router.get("/{setting_id}", response_model=SettingOut)
async def get_setting_by_id(
    setting_id: int,
    _=Depends(require_roles(_ROLES)),
    controller: SettingsController = Depends(get_settings_controller),
):
    """Get a setting by ID."""

    setting = await controller.get_by_id(setting_id)

    if not setting:
        raise HTTPException(status_code=404, detail="Configuración no encontrada")

    return setting


@router.get("/{setting_id}/history", response_model=list[SettingHistoryOut])
async def get_setting_history(
    setting_id: int,
    pagination: PaginationDep,
    _=Depends(require_roles(_ROLES)),
    controller: SettingsController = Depends(get_settings_controller),
):
    """Get setting history by setting ID."""

    setting = await controller.get_by_id(setting_id)

    if not setting:
        raise HTTPException(status_code=404, detail="Configuración no encontrada")

    return await controller.get_history(key=setting["key"], pagination=pagination)


@router.post("/", response_model=SettingOut, status_code=201)
async def create_setting(
    payload: SettingCreate,
    current_user=Depends(require_roles(_ROLES)),
    controller: SettingsController = Depends(get_settings_controller),
):
    """Create a new setting."""

    return await controller.create(payload, current_user)


@router.put("/{setting_id}", response_model=SettingOut)
async def update_setting(
    setting_id: int,
    payload: SettingUpdate,
    current_user=Depends(require_roles(_ROLES)),
    controller: SettingsController = Depends(get_settings_controller),
):
    """Update a setting."""

    setting = await controller.update(setting_id, payload, current_user)

    if not setting:
        raise HTTPException(status_code=404, detail="Configuración no encontrada")

    return setting


@router.delete("/{setting_id}", response_model=SettingOut)
async def delete_setting(
    setting_id: int,
    current_user=Depends(require_roles(_ROLES)),
    controller: SettingsController = Depends(get_settings_controller),
):
    """Delete a setting."""

    setting = await controller.delete(setting_id, current_user)

    if not setting:
        raise HTTPException(status_code=404, detail="Configuración no encontrada")

    return setting
