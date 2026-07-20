"""Dependency injection for setting-related operations."""

from fastapi import Depends

from api.dependencies.audits import get_audit_service
from api.repositories.settings import (
    SettingsRepository,
    get_settings_repository,
)
from api.services.audit_service import AuditService
from api.services.settings_service import SettingService


def get_setting_service(
    settings_repository: SettingsRepository = Depends(get_settings_repository),
    audit_service: AuditService = Depends(get_audit_service),
) -> SettingService:
    """Dependency injection for SettingService."""

    return SettingService(
        settings_repository,
        audit_service,
    )
