"""
Routes for audit log operations.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from api.controllers.audits import AuditsController, get_audits_controller
from api.schemas.audit import AuditCreate, AuditUpdate

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


@router.put("/{audit_id}")
async def update_audit(
    audit_id: int,
    payload: AuditUpdate,
    controller: AuditsController = Depends(get_audits_controller),
):
    """Endpoint to update an audit log."""

    updated_audit = await controller.update(audit_id, payload)

    if not updated_audit:
        return {
            "message": "Audit log not found",
            "status": 404,
            "timestamp": datetime.now(timezone.utc),
        }

    return {
        "message": "Audit log updated successfully",
        "audit": updated_audit,
        "status": 200,
        "timestamp": datetime.now(timezone.utc),
    }


@router.delete("/{audit_id}")
async def delete_audit(
    audit_id: int,
    controller: AuditsController = Depends(get_audits_controller),
):
    """Endpoint to delete an audit log."""

    deleted_audit = await controller.delete(audit_id)

    if not deleted_audit:
        return {
            "message": "Audit log not found",
            "status": 404,
            "timestamp": datetime.now(timezone.utc),
        }

    return {
        "message": "Audit log deleted successfully",
        "audit": deleted_audit,
        "status": 200,
        "timestamp": datetime.now(timezone.utc),
    }
