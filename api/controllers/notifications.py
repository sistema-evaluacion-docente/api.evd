"""
Notifications controller
"""

from fastapi.param_functions import Depends

from api.core.pagination import PaginationParams
from api.dependencies.notifications import get_notification_service
from api.schemas.notification import NotificationCreate, NotificationFilters
from api.services.notification_service import NotificationService


class NotificationsController:
    """Notifications controller"""

    def __init__(self, service: NotificationService):
        self.service = service

    async def get_all(
        self,
        user_id: int,
        filters: NotificationFilters,
        pagination: PaginationParams,
    ):
        """Retrieve all notifications for a user based on filters and pagination."""

        return await self.service.get_all(user_id, filters, pagination)

    async def get_unread_count(self, user_id: int):
        """Get the count of unread notifications for a user."""

        return await self.service.get_unread_count(user_id)

    async def create(
        self,
        data: NotificationCreate,
        actor_id: int | None = None,
    ):
        """Create a new notification."""

        return await self.service.create(data, actor_id)

    async def mark_as_read(self, notification_ids: list[int], user_id: int):
        """Mark specific notifications as read."""

        return await self.service.mark_as_read(notification_ids, user_id)

    async def mark_all_as_read(self, user_id: int):
        """Mark all notifications as read for a user."""

        return await self.service.mark_all_as_read(user_id)


def get_notifications_controller(
    service: NotificationService = Depends(get_notification_service),
):
    """Get notifications controller"""

    return NotificationsController(service)
