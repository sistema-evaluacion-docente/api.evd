"""Extract teacher-specific pages from the PDFs of a UFPS evaluation."""

import io
import os
import re
import tempfile

import pdfplumber
import pikepdf

_TEACHER_CODE_RE = re.compile(
    r"^\s*(\d{5,})\s+[A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ0-9 ]+\s*$",
    re.MULTILINE,
)


def _teacher_page_indexes(pdf_path: str, teacher_code: str) -> list[int]:
    """Indexes of the pages whose teacher header carries `teacher_code`.

    Pre-normalizes through pikepdf before handing to pdfplumber — the
    university's PDFs sometimes contain invalid octal sequences that
    pdfminer (pdfplumber's parser) refuses to handle.
    """

    # Paths stored from Windows uploads use backslashes; normalize for Linux.
    normalized_path = pdf_path.replace("\\", "/")

    matching_indices: list[int] = []
    tmp_path: str | None = None

    try:
        tmp_fd, tmp_path = tempfile.mkstemp(suffix=".pdf")
        os.close(tmp_fd)

        with pikepdf.open(normalized_path) as src:
            src.save(tmp_path)

        with pdfplumber.open(tmp_path) as pdf:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                m = _TEACHER_CODE_RE.search(text)
                if m and m.group(1).strip() == teacher_code:
                    matching_indices.append(i)

    except FileNotFoundError:
        return []
    except Exception:  # noqa: BLE001 — pdfminer, pikepdf, or I/O failures
        return []
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    return matching_indices


def extract_teacher_pages(pdf_paths: list[str], teacher_code: str) -> bytes | None:
    """Return a PDF containing only the pages for the given teacher code.

    Scans each page of every document backing the evaluation for a teacher
    header line matching teacher_code (same regex as
    pdf_parser._parse_teacher_header), so a docente who teaches in the
    presencial and the distancia programs gets both blocks in one report.
    Returns None if the code is not found in any of them.
    """
    pages_by_path = [
        (path, _teacher_page_indexes(path, teacher_code)) for path in pdf_paths
    ]
    pages_by_path = [(path, indexes) for path, indexes in pages_by_path if indexes]

    if not pages_by_path:
        return None

    dst = pikepdf.new()

    for path, indexes in pages_by_path:
        with pikepdf.open(path.replace("\\", "/")) as src:
            for idx in indexes:
                dst.pages.append(src.pages[idx])

    buf = io.BytesIO()
    dst.save(buf)

    return buf.getvalue()
