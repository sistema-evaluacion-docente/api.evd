"""
Storage helpers for improvement plan files.

``UPLOAD_DIR`` is deliberately not mounted as a static directory: these PDFs hold
teacher-sensitive data and are only served through permission-checked endpoints.
"""

import os
import shutil
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


def delete_plan_files(plan_id: int) -> None:
    """Best-effort removal of everything a plan stored on disk.

    Documents and evidences of a plan all live under one directory per plan, so
    dropping it takes the lot. Deleting the row cascades in the database but
    says nothing about the filesystem, which would otherwise keep the PDFs of a
    plan nobody can reach any more.
    """

    directory = os.path.abspath(
        os.path.join(config.UPLOAD_DIR, PLANS_SUBDIR, str(plan_id))
    )
    uploads_root = os.path.abspath(config.UPLOAD_DIR)

    # Never step outside UPLOAD_DIR, whatever the id turns out to be.
    if not directory.startswith(uploads_root + os.sep) or not os.path.isdir(directory):
        return

    shutil.rmtree(directory, ignore_errors=True)
