"""Dependency injection for improvement plan operations."""

from fastapi import Depends

from api.dependencies.audits import get_audit_service
from api.dependencies.notifications import get_notification_service
from api.repositories.improvement_plan_documents import (
    ImprovementPlanDocumentsRepository,
    get_improvement_plan_documents_repository,
)
from api.repositories.improvement_plan_evidences import (
    ImprovementPlanEvidencesRepository,
    get_improvement_plan_evidences_repository,
)
from api.repositories.improvement_plans import (
    ImprovementPlansRepository,
    get_improvement_plans_repository,
)
from api.repositories.settings import SettingsRepository, get_settings_repository
from api.services.audit_service import AuditService
from api.services.improvement_plan_document_service import (
    ImprovementPlanDocumentService,
)
from api.services.improvement_plan_evidence_service import (
    ImprovementPlanEvidenceService,
)
from api.services.improvement_plan_service import ImprovementPlanService
from api.services.notification_service import NotificationService


def get_improvement_plan_service(
    improvement_plans_repository: ImprovementPlansRepository = Depends(
        get_improvement_plans_repository
    ),
    settings_repository: SettingsRepository = Depends(get_settings_repository),
    audit_service: AuditService = Depends(get_audit_service),
    notification_service: NotificationService = Depends(get_notification_service),
) -> ImprovementPlanService:
    """Dependency injection for ImprovementPlanService."""

    return ImprovementPlanService(
        improvement_plans_repository,
        settings_repository,
        audit_service,
        notification_service,
    )


def get_improvement_plan_document_service(
    documents_repository: ImprovementPlanDocumentsRepository = Depends(
        get_improvement_plan_documents_repository
    ),
    improvement_plans_repository: ImprovementPlansRepository = Depends(
        get_improvement_plans_repository
    ),
    plan_service: ImprovementPlanService = Depends(get_improvement_plan_service),
    audit_service: AuditService = Depends(get_audit_service),
    notification_service: NotificationService = Depends(get_notification_service),
) -> ImprovementPlanDocumentService:
    """Dependency injection for ImprovementPlanDocumentService."""

    return ImprovementPlanDocumentService(
        documents_repository,
        improvement_plans_repository,
        plan_service,
        audit_service,
        notification_service,
    )


def get_improvement_plan_evidence_service(
    evidences_repository: ImprovementPlanEvidencesRepository = Depends(
        get_improvement_plan_evidences_repository
    ),
    improvement_plans_repository: ImprovementPlansRepository = Depends(
        get_improvement_plans_repository
    ),
    plan_service: ImprovementPlanService = Depends(get_improvement_plan_service),
    notification_service: NotificationService = Depends(get_notification_service),
    audit_service: AuditService = Depends(get_audit_service),
) -> ImprovementPlanEvidenceService:
    """Dependency injection for ImprovementPlanEvidenceService."""

    return ImprovementPlanEvidenceService(
        evidences_repository,
        improvement_plans_repository,
        plan_service,
        notification_service,
        audit_service,
    )
