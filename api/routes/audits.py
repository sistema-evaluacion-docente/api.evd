"""
Routes for audit log operations.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from api.controllers.audits import AuditsController, get_audits_controller
from api.schemas.audit import AuditCreate

router = APIRouter(prefix="/audits", tags=["Audits"])


@router.post("/")
async def create_audit(
    payload: AuditCreate,
    controller: AuditsController = Depends(get_audits_controller),
):
    """Endpoint to create an audit log."""

    audit = await controller.create(payload)

    return {
        "message": "Audit log created successfully",
        "audit": audit,
        "status": 201,
        "timestamp": datetime.now(timezone.utc),
    }


@router.get("/")
async def get_audits(
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
