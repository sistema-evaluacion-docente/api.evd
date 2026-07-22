"""Routes for audit log operations."""

from fastapi import Depends, HTTPException

from api.controllers.audits import AuditsController, get_audits_controller
from api.core.pagination import PaginationDep
from api.core.router import EnvelopeRouter
from api.middlewares.auth import require_roles
from api.schemas.audit import AuditFiltersDep, AuditOut
from api.schemas.user import RoleName

router = EnvelopeRouter(prefix="/audits", tags=["Audits"])


@router.get("/", response_model=list[AuditOut])
async def get_audits(
    filters: AuditFiltersDep,
    pagination: PaginationDep,
    _=Depends(require_roles([RoleName.ADMIN])),
    controller: AuditsController = Depends(get_audits_controller),
):
    """List all audit logs with pagination and filters."""

    return await controller.get_all(filters, pagination)


@router.get("/{audit_id}", response_model=AuditOut)
async def get_audit_by_id(
    audit_id: int,
    _=Depends(require_roles([RoleName.ADMIN])),
    controller: AuditsController = Depends(get_audits_controller),
):
    """Get an audit log by ID."""

    audit = await controller.get_by_id(audit_id)

    if not audit:
        raise HTTPException(status_code=404, detail="Audit log not found")

    return audit
