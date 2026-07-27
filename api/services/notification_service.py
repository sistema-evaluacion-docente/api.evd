"""Service for notification-related business operations."""

import asyncio
import logging

from api.core.pagination import PaginationParams
from api.core.websockets.connection_manager import connection_manager
from api.core.websockets.events import NotificationEvent
from api.repositories.notifications import NotificationsRepository
from api.schemas.notification import NotificationCreate, NotificationFilters
from api.schemas.pagination import build_paginated_response
from api.serializers.notifications import notification_to_dict
from api.services.audit_service import AuditService

logger = logging.getLogger(__name__)


class NotificationService:
    """Service for notification-related business operations."""

    def __init__(
        self,
        notifications_repository: NotificationsRepository,
        audit_service: AuditService,
    ):
        self.notifications_repository = notifications_repository
        self.audit_service = audit_service

    async def get_all(
        self,
        user_id: int,
        filters: NotificationFilters,
        pagination: PaginationParams,
    ) -> dict:
        """Retrieve all notifications for a user based on filters and pagination."""

        notifications, total = self.notifications_repository.get_by_user(
            user_id, filters, pagination
        )

        items = [notification_to_dict(n) for n in notifications]

        return build_paginated_response(items, total, pagination)

    async def get_unread_count(self, user_id: int) -> int:
        """Get the count of unread notifications for a user."""

        return self.notifications_repository.get_unread_count(user_id)

    async def create(
        self,
        data: NotificationCreate,
        actor_id: int | None = None,
    ) -> dict:
        """Create a new notification and broadcast it via WebSocket."""

        notification = self.notifications_repository.create(data)
        self.notifications_repository.db.commit()
        self.notifications_repository.db.refresh(notification)

        result = notification_to_dict(notification)

        await self._broadcast_notification(notification)

        if actor_id:
            await self.audit_service.log(
                action="CREATE",
                entity_name="notifications",
                entity_id=notification.id,
                actor_id=actor_id,
                description=f"Notificación creada para user_id={data.user_id}: {data.title}",
            )

        return result

    async def mark_as_read(self, notification_ids: list[int], user_id: int) -> int:
        """Mark specific notifications as read for a user."""

        return self.notifications_repository.mark_as_read(notification_ids, user_id)

    async def mark_all_as_read(self, user_id: int) -> int:
        """Mark all notifications as read for a user."""

        return self.notifications_repository.mark_all_as_read(user_id)

    async def _broadcast_notification(self, notification) -> None:
        """Broadcast a notification to the user's WebSocket channel."""

        channel = f"notifications:{notification.user_id}"

        event = NotificationEvent(
            notification_id=notification.id,
            user_id=notification.user_id,
            title=notification.title,
            message=notification.message,
            notification_type=notification.type,
        )

        try:
            try:
                asyncio.get_running_loop()
                asyncio.ensure_future(connection_manager.broadcast(channel, event))
            except RuntimeError:
                asyncio.run(connection_manager.broadcast(channel, event))
        except Exception:
            logger.warning(
                "Failed to broadcast notification %d to channel '%s'",
                notification.id,
                channel,
            )
