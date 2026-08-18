"""
Improvement plan documents repository — generated and signed PDFs of the three
official UFPS forms.
"""

from datetime import datetime, timezone
from typing import Annotated

from fastapi.params import Depends
from sqlalchemy.orm import Session

from api.database import get_db
from api.models.improvement_plan_document import ImprovementPlanDocumentModel
from api.repositories.base import BaseRepository


class ImprovementPlanDocumentsRepository(
    BaseRepository[ImprovementPlanDocumentModel]
):
    """Improvement plan documents repository"""

    def __init__(self, db: Session):
        super().__init__(ImprovementPlanDocumentModel, db)

    def get_by_format(
        self, plan_id: int, format_type: str
    ) -> ImprovementPlanDocumentModel | None:
        """The document row of a plan for one of the official formats."""

        return (
            self.db.query(ImprovementPlanDocumentModel)
            .filter(
                ImprovementPlanDocumentModel.plan_id == plan_id,
                ImprovementPlanDocumentModel.format_type == format_type,
            )
            .first()
        )

    def list_by_plan(self, plan_id: int) -> list[ImprovementPlanDocumentModel]:
        """Every document attached to a plan."""

        return (
            self.db.query(ImprovementPlanDocumentModel)
            .filter(ImprovementPlanDocumentModel.plan_id == plan_id)
            .all()
        )

    def _get_or_create(
        self, plan_id: int, format_type: str
    ) -> ImprovementPlanDocumentModel:
        document = self.get_by_format(plan_id, format_type)

        if document is None:
            document = ImprovementPlanDocumentModel(
                plan_id=plan_id, format_type=format_type
            )
            self.db.add(document)

        return document

    def set_generated(
        self, plan_id: int, format_type: str, file_url: str, generated_by: int | None
    ) -> tuple[ImprovementPlanDocumentModel, str | None]:
        """Record a freshly rendered PDF.

        Returns the row plus the path it replaced, so the caller can drop the
        stale file from disk.
        """

        document = self._get_or_create(plan_id, format_type)
        previous = document.generated_pdf_url

        document.generated_pdf_url = file_url
        document.generated_at = datetime.now(timezone.utc)
        document.generated_by = generated_by

        self.db.commit()
        self.db.refresh(document)
        self._emit_db_event("INSERT", document.id)

        return document, previous

    def set_signed(
        self,
        plan_id: int,
        format_type: str,
        file_url: str,
        signed_by: int | None,
        filename: str | None = None,
    ) -> tuple[ImprovementPlanDocumentModel, str | None]:
        """Record the scanned copy that carries the handwritten signatures."""

        document = self._get_or_create(plan_id, format_type)
        previous = document.signed_pdf_url

        document.signed_pdf_url = file_url
        document.signed_filename = filename
        document.signed_at = datetime.now(timezone.utc)
        document.signed_by = signed_by

        self.db.commit()
        self.db.refresh(document)
        self._emit_db_event("INSERT", document.id)

        return document, previous

    def clear_signed(self, plan_id: int, format_type: str) -> str | None:
        """Drop the signed copy, leaving the generated one untouched.

        Returns the path that was attached, so the caller can remove the file
        from disk. ``None`` when there was nothing signed to begin with.
        """

        document = self.get_by_format(plan_id, format_type)

        if document is None or document.signed_pdf_url is None:
            return None

        previous = document.signed_pdf_url

        document.signed_pdf_url = None
        document.signed_filename = None
        document.signed_at = None
        document.signed_by = None

        self.db.commit()
        self.db.refresh(document)
        self._emit_db_event("UPDATE", document.id)

        return previous


def get_improvement_plan_documents_repository(
    db: Annotated[Session, Depends(get_db)],
):
    """Get improvement plan documents repository"""

    return ImprovementPlanDocumentsRepository(db)
