"""WebSocket routes for evaluations."""

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from api.core.websockets.connection_manager import connection_manager
from api.middlewares.auth import verify_token
from api.services.user_service import UserService
from api.database import SessionLocal
from api.schemas.user import RoleName
from api.repositories.users import UsersRepository
from api.repositories.audits import AuditsRepository
from api.services.audit_service import AuditService
from api.models.evaluation import EvaluationModel

logger = logging.getLogger(__name__)

router = APIRouter()

_EVAL_ROLES = {RoleName.ADMIN.value, RoleName.DIRECTOR_DE_DEPARTAMENTO.value}


async def _authenticate_ws(token: str | None) -> dict | None:
    """Authenticate the WebSocket connection using the provided token."""

    if not token:
        return None
    try:
        decoded = verify_token(token)
        return decoded
    except Exception:
        return None


async def _check_evaluation_access(uid: str, evaluation_id: int) -> bool:
    """Check if the user has access to the evaluation."""

    db = SessionLocal()

    try:
        users_repository = UsersRepository(db)
        audits_repository = AuditsRepository(db)
        audit_service = AuditService(audits_repository)
        user_service = UserService(users_repository, audit_service)

        user = await user_service.get_by_uid(uid)

        if not user:
            return False

        user_roles = set(user.get("roles", []))

        if not user_roles.intersection(_EVAL_ROLES):
            return False

        evaluation = (
            db.query(EvaluationModel)
            .filter(EvaluationModel.id == evaluation_id)
            .first()
        )

        return evaluation is not None
    finally:
        db.close()


@router.websocket("/ws/evaluations/{evaluation_id}")
async def ws_evaluation(
    websocket: WebSocket, evaluation_id: int, token: str | None = None
):
    """WebSocket endpoint for evaluation updates."""

    decoded = await _authenticate_ws(token)

    if not decoded:
        await websocket.close(code=4001, reason="Authentication failed")
        return

    uid = decoded.get("user_id")
    has_access = await _check_evaluation_access(uid, evaluation_id)

    if not has_access:
        await websocket.close(code=4003, reason="Forbidden")
        return

    channel = f"eval:{evaluation_id}"

    await connection_manager.connect(websocket, channel)

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await connection_manager.disconnect(websocket, channel)
