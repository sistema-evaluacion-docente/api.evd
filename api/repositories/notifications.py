"""
Notifications repository
"""

from typing import Annotated

from fastapi.params import Depends
from sqlalchemy import or_
from sqlalchemy.orm import Session

from api.core.pagination import PaginationParams
from api.database import get_db
from api.models.notification import NotificationModel
from api.repositories.base import BaseRepository
from api.schemas.notification import NotificationFilters


class NotificationsRepository(BaseRepository[NotificationModel]):
    """Notifications repository"""

    def __init__(self, db: Session):
        super().__init__(NotificationModel, db)

    def get_by_user(
        self,
        user_id: int,
        filters: NotificationFilters,
        pagination: PaginationParams,
    ) -> tuple[list[NotificationModel], int]:
        """Retrieve notifications for a user with filters and pagination."""

        query = self.db.query(NotificationModel).filter(
            NotificationModel.user_id == user_id
        )

        if filters.type is not None:
            query = query.filter(NotificationModel.type == filters.type)

        if filters.read is not None:
            query = query.filter(NotificationModel.read == filters.read)

        if filters.search:
            search_pattern = f"%{filters.search}%"
            query = query.filter(
                or_(
                    NotificationModel.title.ilike(search_pattern),
                    NotificationModel.message.ilike(search_pattern),
                )
            )

        query = query.order_by(NotificationModel.created_at.desc())

        return self.paginate(query, pagination)

    def get_unread_count(self, user_id: int) -> int:
        """Get the count of unread notifications for a user."""

        return (
            self.db.query(NotificationModel)
            .filter(
                NotificationModel.user_id == user_id,
                NotificationModel.read == False,
            )
            .count()
        )

    def mark_as_read(self, notification_ids: list[int], user_id: int) -> int:
        """Mark specific notifications as read for a user. Returns the count of updated rows."""

        if not notification_ids:
            return 0

        count = (
            self.db.query(NotificationModel)
            .filter(
                NotificationModel.id.in_(notification_ids),
                NotificationModel.user_id == user_id,
            )
            .update({"read": True}, synchronize_session="fetch")
        )

        self.db.commit()

        return count

    def mark_all_as_read(self, user_id: int) -> int:
        """Mark all notifications as read for a user. Returns the count of updated rows."""

        count = (
            self.db.query(NotificationModel)
            .filter(
                NotificationModel.user_id == user_id,
                NotificationModel.read == False,
            )
            .update({"read": True}, synchronize_session="fetch")
        )

        self.db.commit()

        return count


def get_notifications_repository(db: Annotated[Session, Depends(get_db)]):
    """Get notifications repository"""

    return NotificationsRepository(db)
