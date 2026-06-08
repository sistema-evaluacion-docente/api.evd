"""
Routes for audit log operations.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from api.controllers.audits import AuditsController, get_audits_controller
from api.middlewares.auth import require_roles
from api.schemas.user import RoleName

router = APIRouter(prefix="/audits", tags=["Audits"])


@router.get("/")
async def get_audits(
    _: dict = Depends(require_roles([RoleName.ADMIN])),
    controller: AuditsController = Depends(get_audits_controller),
):
    """Endpoint to get all audit logs."""

    audits = await controller.get_all()

    return {
        "data": audits,
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
