"""
Improvement plan evidences repository — the deliverables the director asks for,
the files the teacher submits and the conversation around them.
"""

from datetime import datetime, timezone
from typing import Annotated

from fastapi.params import Depends
from sqlalchemy.orm import Session

from api.database import get_db
from api.models.improvement_plan_evidence import ImprovementPlanEvidenceModel
from api.models.improvement_plan_evidence_comment import (
    ImprovementPlanEvidenceCommentModel,
)
from api.models.improvement_plan_evidence_request import (
    ImprovementPlanEvidenceRequestModel,
)
from api.models.user import UserModel
from api.repositories.base import BaseRepository
from api.schemas.improvement_plan import (
    ImprovementPlanEvidenceRequestCreate,
    ImprovementPlanEvidenceRequestUpdate,
)
from api.serializers.improvement_plans import (
    improvement_plan_evidence_comment_to_dict,
    improvement_plan_evidence_request_to_dict,
    improvement_plan_evidence_to_dict,
)


class ImprovementPlanEvidencesRepository(
    BaseRepository[ImprovementPlanEvidenceRequestModel]
):
    """Improvement plan evidences repository"""

    def __init__(self, db: Session):
        super().__init__(ImprovementPlanEvidenceRequestModel, db)

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _author_names(self, request) -> dict[int, str]:
        """Display names for everyone appearing in a request thread."""

        ids = {c.author_id for c in request.comments if c.author_id}
        ids |= {e.uploaded_by for e in request.evidences if e.uploaded_by}

        if not ids:
            return {}

        rows = (
            self.db.query(UserModel.id, UserModel.name)
            .filter(UserModel.id.in_(ids))
            .all()
        )

        return {row[0]: row[1] for row in rows}

    def _enrich(self, request) -> dict:
        return improvement_plan_evidence_request_to_dict(
            request, author_names=self._author_names(request)
        )

    # ------------------------------------------------------------------ #
    # Requests
    # ------------------------------------------------------------------ #
    def get_request(
        self, plan_id: int, request_id: int
    ) -> ImprovementPlanEvidenceRequestModel | None:
        """A request of the given plan, or None if it belongs elsewhere."""

        return (
            self.db.query(ImprovementPlanEvidenceRequestModel)
            .filter(
                ImprovementPlanEvidenceRequestModel.id == request_id,
                ImprovementPlanEvidenceRequestModel.plan_id == plan_id,
            )
            .first()
        )

    async def list_requests(self, plan_id: int) -> list[dict]:
        """Every deliverable requested on a plan, newest last."""

        requests = (
            self.db.query(ImprovementPlanEvidenceRequestModel)
            .filter(ImprovementPlanEvidenceRequestModel.plan_id == plan_id)
            .order_by(ImprovementPlanEvidenceRequestModel.created_at)
            .all()
        )

        return [self._enrich(r) for r in requests]

    async def get_request_detail(self, plan_id: int, request_id: int) -> dict | None:
        """One request with its submissions and thread."""

        request = self.get_request(plan_id, request_id)

        return self._enrich(request) if request else None

    async def create_request(
        self,
        plan_id: int,
        data: ImprovementPlanEvidenceRequestCreate,
        requested_by: int | None = None,
    ) -> dict:
        """Ask the teacher for a specific deliverable."""

        request = ImprovementPlanEvidenceRequestModel(
            plan_id=plan_id,
            item_id=data.item_id,
            requested_by=requested_by,
            title=data.title,
            description=data.description,
            due_date=data.due_date,
            status="PENDIENTE",
        )

        self.db.add(request)
        self.db.commit()
        self.db.refresh(request)
        self._emit_db_event("INSERT", request.id)

        return self._enrich(request)

    async def update_request(
        self, plan_id: int, request_id: int, data: ImprovementPlanEvidenceRequestUpdate
    ) -> dict | None:
        """Edit a request or move it along its state machine."""

        request = self.get_request(plan_id, request_id)

        if not request:
            return None

        payload = data.model_dump(exclude_unset=True)

        if "status" in payload and payload["status"] is not None:
            payload["status"] = payload["status"].value

        for field, value in payload.items():
            setattr(request, field, value)

        self.db.commit()
        self.db.refresh(request)

        return self._enrich(request)

    def set_request_status(self, request_id: int, status: str) -> None:
        """Move a request to a new state without reloading it."""

        request = (
            self.db.query(ImprovementPlanEvidenceRequestModel)
            .filter(ImprovementPlanEvidenceRequestModel.id == request_id)
            .first()
        )

        if request:
            request.status = status
            self.db.commit()

    # ------------------------------------------------------------------ #
    # Thread
    # ------------------------------------------------------------------ #
    async def add_comment(
        self,
        request_id: int,
        body: str,
        author_id: int | None = None,
        is_system: bool = False,
    ) -> dict:
        """Post a message on a request thread."""

        comment = ImprovementPlanEvidenceCommentModel(
            request_id=request_id,
            author_id=author_id,
            body=body,
            is_system=is_system,
        )

        self.db.add(comment)
        self.db.commit()
        self.db.refresh(comment)
        self._emit_db_event("INSERT", comment.id)

        author_name = None
        if comment.author_id:
            row = (
                self.db.query(UserModel.name)
                .filter(UserModel.id == comment.author_id)
                .first()
            )
            author_name = row[0] if row else None

        return improvement_plan_evidence_comment_to_dict(
            comment, author_name=author_name
        )

    # ------------------------------------------------------------------ #
    # Evidences
    # ------------------------------------------------------------------ #
    def get_evidence(
        self, plan_id: int, evidence_id: int
    ) -> ImprovementPlanEvidenceModel | None:
        """An evidence of the given plan, or None if it belongs elsewhere."""

        return (
            self.db.query(ImprovementPlanEvidenceModel)
            .filter(
                ImprovementPlanEvidenceModel.id == evidence_id,
                ImprovementPlanEvidenceModel.plan_id == plan_id,
            )
            .first()
        )

    async def add_evidence(
        self,
        plan_id: int,
        file_url: str,
        description: str | None = None,
        item_id: int | None = None,
        request_id: int | None = None,
        uploaded_by: int | None = None,
    ) -> dict:
        """Attach a submitted file, optionally answering a request."""

        evidence = ImprovementPlanEvidenceModel(
            plan_id=plan_id,
            item_id=item_id,
            request_id=request_id,
            uploaded_by=uploaded_by,
            description=(description.strip() or None) if description else None,
            file_url=file_url,
            status="PENDIENTE",
        )

        self.db.add(evidence)
        self.db.commit()
        self.db.refresh(evidence)
        self._emit_db_event("INSERT", evidence.id)

        return improvement_plan_evidence_to_dict(evidence)

    async def review_evidence(
        self, evidence_id: int, status: str, reviewed_by: int | None
    ) -> dict | None:
        """Record the director's verdict on a submitted evidence."""

        evidence = (
            self.db.query(ImprovementPlanEvidenceModel)
            .filter(ImprovementPlanEvidenceModel.id == evidence_id)
            .first()
        )

        if not evidence:
            return None

        evidence.status = status
        evidence.reviewed_by = reviewed_by
        evidence.reviewed_at = datetime.now(timezone.utc)

        self.db.commit()
        self.db.refresh(evidence)

        return improvement_plan_evidence_to_dict(evidence)

    async def delete_evidence(self, plan_id: int, evidence_id: int) -> str | None:
        """Delete an evidence, returning the file path so it can be removed."""

        evidence = self.get_evidence(plan_id, evidence_id)

        if not evidence:
            return None

        file_url = evidence.file_url
        self.db.delete(evidence)
        self.db.commit()
        self._emit_db_event("DELETE", evidence_id)

        return file_url


def get_improvement_plan_evidences_repository(
    db: Annotated[Session, Depends(get_db)],
):
    """Get improvement plan evidences repository"""

    return ImprovementPlanEvidencesRepository(db)
