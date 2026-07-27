"""
Routes for notification operations.
"""

from fastapi import Depends

from api.controllers.notifications import (
    NotificationsController,
    get_notifications_controller,
)
from api.core.pagination import PaginationDep
from api.core.router import EnvelopeRouter
from api.middlewares.auth import require_roles
from api.schemas.notification import (
    NotificationCreate,
    NotificationFiltersDep,
    NotificationMarkRead,
    NotificationOut,
)
from api.schemas.user import RoleName

router = EnvelopeRouter(prefix="/notifications", tags=["Notifications"])

_ALL_ROLES = [RoleName.ADMIN, RoleName.DIRECTOR_DE_DEPARTAMENTO, RoleName.DOCENTE]


@router.get(
    "/me",
    response_model=list[NotificationOut],
    responses={401: {"description": "Unauthorized"}},
)
async def get_my_notifications(
    filters: NotificationFiltersDep,
    pagination: PaginationDep,
    current_user=Depends(require_roles(_ALL_ROLES)),
    controller: NotificationsController = Depends(get_notifications_controller),
):
    """List current user's notifications with optional filters and pagination."""

    return await controller.get_all(current_user["id"], filters, pagination)


@router.get(
    "/me/unread-count",
    response_model=dict,
    responses={401: {"description": "Unauthorized"}},
)
async def get_my_unread_count(
    current_user=Depends(require_roles(_ALL_ROLES)),
    controller: NotificationsController = Depends(get_notifications_controller),
):
    """Get the count of unread notifications for the current user."""

    count = await controller.get_unread_count(current_user["id"])

    return {"unread_count": count}


@router.post(
    "/",
    response_model=NotificationOut,
    status_code=201,
    responses={403: {"description": "Forbidden"}},
)
async def create_notification(
    data: NotificationCreate,
    current_user=Depends(require_roles([RoleName.ADMIN, RoleName.DIRECTOR_DE_DEPARTAMENTO])),
    controller: NotificationsController = Depends(get_notifications_controller),
):
    """Create a new notification (admin/director only)."""

    return await controller.create(data, actor_id=current_user["id"])


@router.put(
    "/me/read",
    response_model=dict,
    responses={401: {"description": "Unauthorized"}},
)
async def mark_my_notifications_read(
    payload: NotificationMarkRead,
    current_user=Depends(require_roles(_ALL_ROLES)),
    controller: NotificationsController = Depends(get_notifications_controller),
):
    """Mark specific notifications as read for the current user."""

    count = await controller.mark_as_read(payload.ids, current_user["id"])

    return {"updated": count}


@router.put(
    "/me/read-all",
    response_model=dict,
    responses={401: {"description": "Unauthorized"}},
)
async def mark_all_my_notifications_read(
    current_user=Depends(require_roles(_ALL_ROLES)),
    controller: NotificationsController = Depends(get_notifications_controller),
):
    """Mark all notifications as read for the current user."""

    count = await controller.mark_all_as_read(current_user["id"])

    return {"updated": count}
