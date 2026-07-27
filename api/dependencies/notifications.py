"""Dependency injection for notification-related operations."""

from fastapi import Depends

from api.dependencies.audits import get_audit_service
from api.repositories.notifications import (
    NotificationsRepository,
    get_notifications_repository,
)
from api.services.audit_service import AuditService
from api.services.notification_service import NotificationService


def get_notification_service(
    notifications_repository: NotificationsRepository = Depends(
        get_notifications_repository
    ),
    audit_service: AuditService = Depends(get_audit_service),
) -> NotificationService:
    """Dependency injection for NotificationService."""

    return NotificationService(notifications_repository, audit_service)
