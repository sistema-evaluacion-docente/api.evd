"""
Storage helpers for the PDFs of an evaluation.

The university publishes one document per kind of program, so an evaluation can
be backed by one or two files and ``evaluations.pdf_url`` holds their paths
separated by commas. Each file is stored under a name that starts with its
modality, so a single path can be told apart later without reopening the PDF.
"""

import os
import uuid

from api.utils.modalities import normalize_modality

PDF_URL_SEPARATOR = ","

# Prefijo de los PDFs subidos antes de que existiera la modalidad.
UNKNOWN_MODALITY_PREFIX = "evaluacion"


def split_pdf_urls(pdf_url: str | None) -> list[str]:
    """Split the stored column into the individual PDF paths."""

    if not pdf_url:
        return []

    return [path.strip() for path in pdf_url.split(PDF_URL_SEPARATOR) if path.strip()]


def join_pdf_urls(paths: list[str]) -> str:
    """Join the paths of an evaluation's PDFs into the stored column."""

    return PDF_URL_SEPARATOR.join(paths)


def stored_pdf_filename(modality: str | None) -> str:
    """Build the name a freshly uploaded PDF is stored under."""

    prefix = normalize_modality(modality)
    prefix = prefix.lower() if prefix else UNKNOWN_MODALITY_PREFIX

    return f"{prefix}_{uuid.uuid4().hex}.pdf"


def pdf_url_modality(path: str) -> str | None:
    """Read back the modality a stored PDF was saved under, from its name.

    Returns None for files uploaded before the modality was part of the name."""

    return normalize_modality(os.path.basename(path).split("_", 1)[0])


def select_pdf_url(pdf_url: str | None, modality: str | None = None) -> str | None:
    """Pick one of an evaluation's PDFs.

    Without a modality the first one is served, which is what an evaluation
    backed by a single PDF has always done. With one, only a file stored under
    that modality matches — None when the evaluation has no such document."""

    paths = split_pdf_urls(pdf_url)

    if not paths:
        return None

    if modality is None:
        return paths[0]

    wanted = normalize_modality(modality)

    return next((path for path in paths if pdf_url_modality(path) == wanted), None)
