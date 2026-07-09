"""
Routes for audit log operations.
"""

from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, Query

from api.controllers.audits import AuditsController, get_audits_controller
from api.middlewares.auth import require_roles
from api.schemas.audit import AuditDetailResponse, AuditListResponse
from api.schemas.user import RoleName

router = APIRouter(prefix="/audits", tags=["Audits"])


@router.get(
    "/",
    response_model=AuditListResponse,
    responses={403: {"description": "Forbidden"}},
)
async def get_audits(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    table_name: str | None = Query(None, description="Filter by table name"),
    operation: str | None = Query(None, description="Filter by operation"),
    search: str | None = Query(
        None, description="Search in element, description, user_id"
    ),
    start_date: date | None = Query(None, description="Filter logs from this date"),
    end_date: date | None = Query(None, description="Filter logs until this date"),
    _: dict = Depends(require_roles([RoleName.ADMIN])),
    controller: AuditsController = Depends(get_audits_controller),
):
    """Endpoint to get paginated audit logs."""

    audits = await controller.get_all(
        page=page,
        limit=limit,
        table_name=table_name,
        operation=operation,
        search=search,
        start_date=start_date,
        end_date=end_date,
    )

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


@router.get(
    "/{audit_id}",
    response_model=AuditDetailResponse,
    responses={404: {"model": AuditDetailResponse}, 403: {"description": "Forbidden"}},
)
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
