"""Routes for setting operations.

Settings come in two scopes: the institutional ones an ADMIN maintains, and
the per-department ones each director maintains for its own department. A
director only reaches its own department's settings — the service pins the
scope, these routes just hand it the authenticated user.
"""

from fastapi import Depends, HTTPException, Query

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

_ROLES = [RoleName.ADMIN, RoleName.DIRECTOR_DE_DEPARTAMENTO]


@router.get("/", response_model=list[SettingOut])
async def get_all_settings(
    filters: SettingFiltersDep,
    pagination: PaginationDep,
    current_user=Depends(require_roles(_ROLES)),
    controller: SettingsController = Depends(get_settings_controller),
):
    """List the settings the user may see, with pagination and filters."""

    return await controller.get_all(filters, pagination, current_user)


@router.get("/by-key/{key}", response_model=SettingOut)
async def get_setting_by_key(
    key: str,
    department_id: int | None = Query(default=None),
    current_user=Depends(require_roles(_ROLES)),
    controller: SettingsController = Depends(get_settings_controller),
):
    """Get the setting in effect for a key.

    The department's own value wins; the institutional one is the fallback.
    """

    setting = await controller.get_by_key(key, current_user, department_id)

    if not setting:
        raise HTTPException(status_code=404, detail="Configuración no encontrada")

    return setting


@router.get("/{setting_id}", response_model=SettingOut)
async def get_setting_by_id(
    setting_id: int,
    current_user=Depends(require_roles(_ROLES)),
    controller: SettingsController = Depends(get_settings_controller),
):
    """Get a setting by ID."""

    setting = await controller.get_by_id(setting_id, current_user)

    if not setting:
        raise HTTPException(status_code=404, detail="Configuración no encontrada")

    return setting


@router.get("/{setting_id}/history", response_model=list[SettingHistoryOut])
async def get_setting_history(
    setting_id: int,
    pagination: PaginationDep,
    current_user=Depends(require_roles(_ROLES)),
    controller: SettingsController = Depends(get_settings_controller),
):
    """Get the history of a setting, in its own scope."""

    setting = await controller.get_by_id(setting_id, current_user)

    if not setting:
        raise HTTPException(status_code=404, detail="Configuración no encontrada")

    return await controller.get_history(
        key=setting["key"],
        pagination=pagination,
        department_id=setting["department_id"],
    )


@router.post("/", response_model=SettingOut, status_code=201)
async def create_setting(
    payload: SettingCreate,
    current_user=Depends(require_roles(_ROLES)),
    controller: SettingsController = Depends(get_settings_controller),
):
    """Create a new setting.

    A director creates it for its own department; an ADMIN creates an
    institutional setting, or one for the department it names in the payload.
    """

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
