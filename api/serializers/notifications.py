"""Serializer for NotificationModel to dictionary representation."""

from api.models.notification import NotificationModel


def notification_to_dict(notification: NotificationModel) -> dict:
    """Convert NotificationModel instance to dictionary."""

    return {
        "id": notification.id,
        "user_id": notification.user_id,
        "title": notification.title,
        "message": notification.message,
        "type": notification.type,
        "read": notification.read,
        "created_at": notification.created_at,
        "updated_at": notification.updated_at,
    }
