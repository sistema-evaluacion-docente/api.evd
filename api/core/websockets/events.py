"""WebSocket event models."""

from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, Field


class BaseWebSocketEvent(BaseModel):
    """Base model for WebSocket events."""

    type: str
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class EvaluationProgressEvent(BaseWebSocketEvent):
    """Event model for evaluation progress updates."""

    type: Literal["evaluation_progress"] = "evaluation_progress"
    evaluation_id: int
    stage: Literal["UPLOADING", "ANALYZING"]
    status: Optional[str] = None
    ai_status: Optional[str] = None
    count: Optional[int] = None


class EvaluationLogEvent(BaseWebSocketEvent):
    """Event model for detailed evaluation processing logs."""

    type: Literal["evaluation_log"] = "evaluation_log"
    evaluation_id: int
    level: Literal["info", "success", "warning", "error"] = "info"
    message: str
    teacher_name: Optional[str] = None
    teacher_code: Optional[str] = None
    course_name: Optional[str] = None
    course_code: Optional[str] = None


class DevLogEvent(BaseWebSocketEvent):
    """Event model for developer logs."""

    type: Literal["dev_log"] = "dev_log"
    category: Literal["request", "response", "db_write"]
    method: Optional[str] = None
    path: Optional[str] = None
    query_params: Optional[dict] = None
    status_code: Optional[int] = None
    duration_ms: Optional[float] = None
    operation: Optional[str] = None
    model: Optional[str] = None
    record_id: Optional[int] = None
    details: Optional[dict] = None
    detail: Optional[str] = None
