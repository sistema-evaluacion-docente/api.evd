"""
Storage helpers for improvement plan files.

``UPLOAD_DIR`` is deliberately not mounted as a static directory: these PDFs hold
teacher-sensitive data and are only served through permission-checked endpoints.
"""

import os
import uuid

from api.config import config

PLANS_SUBDIR = "improvement_plans"


def plan_documents_dir(plan_id: int) -> str:
    """Directory holding the official form PDFs of a plan."""

    return os.path.join(config.UPLOAD_DIR, PLANS_SUBDIR, str(plan_id), "documents")


def save_plan_document(plan_id: int, pdf_bytes: bytes, prefix: str) -> str:
    """Persist a PDF for a plan and return its path on disk."""

    directory = plan_documents_dir(plan_id)
    os.makedirs(directory, exist_ok=True)

    filepath = os.path.join(directory, f"{prefix}_{uuid.uuid4().hex}.pdf")

    with open(filepath, "wb") as handle:
        handle.write(pdf_bytes)

    return filepath


def plan_evidences_dir(plan_id: int) -> str:
    """Directory holding the evidence files submitted for a plan."""

    return os.path.join(config.UPLOAD_DIR, PLANS_SUBDIR, str(plan_id), "evidences")


def save_plan_evidence(plan_id: int, pdf_bytes: bytes) -> str:
    """Persist a submitted evidence and return its path on disk."""

    directory = plan_evidences_dir(plan_id)
    os.makedirs(directory, exist_ok=True)

    filepath = os.path.join(directory, f"evidencia_{uuid.uuid4().hex}.pdf")

    with open(filepath, "wb") as handle:
        handle.write(pdf_bytes)

    return filepath


def delete_plan_file(filepath: str | None) -> None:
    """Best-effort removal of a replaced file, only ever inside UPLOAD_DIR."""

    if not filepath:
        return

    uploads_root = os.path.abspath(config.UPLOAD_DIR)
    target = os.path.abspath(filepath)

    if target.startswith(uploads_root + os.sep) and os.path.isfile(target):
        try:
            os.remove(target)
        except OSError:
            pass
