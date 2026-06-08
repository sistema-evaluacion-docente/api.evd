"""
Routes for audit log operations.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query

from api.controllers.audits import AuditsController, get_audits_controller
from api.middlewares.auth import require_roles
from api.schemas.user import RoleName

router = APIRouter(prefix="/audits", tags=["Audits"])


@router.get("/")
async def get_audits(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    _: dict = Depends(require_roles([RoleName.ADMIN])),
    controller: AuditsController = Depends(get_audits_controller),
):
    """Endpoint to get paginated audit logs."""

    audits = await controller.get_all(page=page, limit=limit)

    return {
        "data": audits["items"],
        "pagination": {
            "total": audits["total"],
            "page": audits["page"],
            "limit": audits["limit"],
            "pages": audits["pages"],
        },
        "error": None,
        "status": 200,
        "timestamp": datetime.now(timezone.utc),
    }


@router.get("/{audit_id}")
async def get_audit_by_id(
    audit_id: int,
    _: dict = Depends(require_roles([RoleName.ADMIN])),
    controller: AuditsController = Depends(get_audits_controller),
):
    """Endpoint to get an audit log by ID."""

    audit = await controller.get_by_id(audit_id)

    if not audit:
        return {
            "data": None,
            "error": "Audit log not found",
            "status": 404,
            "timestamp": datetime.now(timezone.utc),
        }

    return {
        "data": audit,
        "error": None,
        "status": 200,
        "timestamp": datetime.now(timezone.utc),
    }
