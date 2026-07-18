"""
Routes for settings operations.
"""

from fastapi import Depends, Query

from api.controllers.settings import (
    SettingsController,
    get_settings_controller,
)
from api.core.router import EnvelopeRouter
from api.middlewares.auth import get_current_user, require_roles
from api.schemas.pagination import Pagination
from api.schemas.response import ResponseSchema
from api.schemas.setting import (
    SettingCreate,
    SettingDetailResponse,
    SettingHistoryListResponse,
    SettingListResponse,
    SettingUpdate,
)
from api.schemas.user import RoleName

router = EnvelopeRouter(prefix="/settings", tags=["Settings"])


@router.get(
    "/",
    response_model=SettingListResponse,
    responses={403: {"description": "Forbidden"}},
)
async def get_all_settings(
    search: str | None = Query(default=None, min_length=1),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=100),
    _=Depends(require_roles([RoleName.ADMIN])),
    controller: SettingsController = Depends(get_settings_controller),
):
    settings = await controller.get_all(search=search, page=page, limit=limit)

    if settings is None:
        return ResponseSchema(
            status=400, message="Error getting settings", path="/settings"
        )

    return ResponseSchema(
        status=200,
        message="Settings found",
        data=settings["items"],
        pagination=Pagination(
            limit=settings["limit"],
            total=settings["total"],
            pages=settings["pages"],
            page=settings["page"],
        ),
        path="/settings",
    )


@router.get(
    "/by-key/{key}",
    response_model=SettingDetailResponse,
    responses={403: {"description": "Forbidden"}, 404: {"model": ResponseSchema}},
)
async def get_setting_by_key(
    key: str,
    _=Depends(require_roles([RoleName.ADMIN])),
    controller: SettingsController = Depends(get_settings_controller),
):
    setting = await controller.get_by_key(key)

    if not setting:
        return ResponseSchema(
            status=404,
            message="Setting not found",
            path=f"/settings/by-key/{key}",
        )

    return ResponseSchema(
        status=200,
        message="Setting found",
        data=setting,
        path=f"/settings/by-key/{key}",
    )


@router.get(
    "/{setting_id}",
    response_model=SettingDetailResponse,
    responses={403: {"description": "Forbidden"}, 404: {"model": ResponseSchema}},
)
async def get_setting_by_id(
    setting_id: int,
    _=Depends(require_roles([RoleName.ADMIN])),
    controller: SettingsController = Depends(get_settings_controller),
):
    setting = await controller.get_by_id(setting_id)

    if not setting:
        return ResponseSchema(
            status=404,
            message="Setting not found",
            path=f"/settings/{setting_id}",
        )

    return ResponseSchema(
        status=200,
        message="Setting found",
        data=setting,
        path=f"/settings/{setting_id}",
    )


@router.get(
    "/{setting_id}/history",
    response_model=SettingHistoryListResponse,
    responses={403: {"description": "Forbidden"}},
)
async def get_setting_history(
    setting_id: int,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=100),
    _=Depends(require_roles([RoleName.ADMIN])),
    controller: SettingsController = Depends(get_settings_controller),
):
    history = await controller.get_history(
        setting_id=setting_id, page=page, limit=limit
    )

    if history is None:
        return ResponseSchema(
            status=400,
            message="Error getting setting history",
            path=f"/settings/{setting_id}/history",
        )

    return ResponseSchema(
        status=200,
        message="Setting history found",
        data=history["items"],
        pagination=Pagination(
            limit=history["limit"],
            total=history["total"],
            pages=history["pages"],
            page=history["page"],
        ),
        path=f"/settings/{setting_id}/history",
    )


@router.post(
    "/",
    response_model=SettingDetailResponse,
    responses={400: {"model": ResponseSchema}, 403: {"description": "Forbidden"}},
    status_code=201,
)
async def create_setting(
    payload: SettingCreate,
    current_user=Depends(get_current_user),
    _=Depends(require_roles([RoleName.ADMIN])),
    controller: SettingsController = Depends(get_settings_controller),
):
    try:
        setting = await controller.create(payload, current_user)
    except ValueError as e:
        return ResponseSchema(
            status=400,
            message=str(e),
            path="/settings",
        )

    return ResponseSchema(
        status=201,
        message="Setting created successfully",
        data=setting,
        path="/settings",
    )


@router.put(
    "/{setting_id}",
    response_model=SettingDetailResponse,
    responses={400: {"model": ResponseSchema}, 403: {"description": "Forbidden"}},
)
async def update_setting(
    setting_id: int,
    payload: SettingUpdate,
    current_user=Depends(get_current_user),
    _=Depends(require_roles([RoleName.ADMIN])),
    controller: SettingsController = Depends(get_settings_controller),
):
    setting = await controller.update(setting_id, payload, current_user)

    if not setting:
        return ResponseSchema(
            status=404,
            message="Setting not found",
            path=f"/settings/{setting_id}",
        )

    return ResponseSchema(
        status=200,
        message="Setting updated successfully",
        data=setting,
        path=f"/settings/{setting_id}",
    )


@router.delete(
    "/{setting_id}",
    response_model=SettingDetailResponse,
    responses={400: {"model": ResponseSchema}, 403: {"description": "Forbidden"}},
)
async def delete_setting(
    setting_id: int,
    current_user=Depends(get_current_user),
    _=Depends(require_roles([RoleName.ADMIN])),
    controller: SettingsController = Depends(get_settings_controller),
):
    setting = await controller.delete(setting_id, current_user)

    if not setting:
        return ResponseSchema(
            status=404,
            message="Setting not found",
            path=f"/settings/{setting_id}",
        )

    return ResponseSchema(
        status=200,
        message="Setting deleted successfully",
        data=setting,
        path=f"/settings/{setting_id}",
    )
