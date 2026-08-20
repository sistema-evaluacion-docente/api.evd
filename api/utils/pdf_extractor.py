"""Extract teacher-specific pages from a UFPS evaluation PDF."""

import io
import re

import pdfplumber
import pikepdf

_TEACHER_CODE_RE = re.compile(
    r"^\s*(\d{5,})\s+[A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ0-9 ]+\s*$",
    re.MULTILINE,
)


def extract_teacher_pages(pdf_path: str, teacher_code: str) -> bytes | None:
    """Return a PDF containing only the pages for the given teacher code.

    Scans each page for a teacher-header line matching teacher_code (same
    regex as pdf_parser._parse_teacher_header). Returns None if the code is
    not found anywhere in the document or if the file does not exist on disk.
    """
    # Paths stored from Windows uploads use backslashes; normalize for Linux.
    normalized_path = pdf_path.replace("\\", "/")

    matching_indices: list[int] = []

    try:
        with pdfplumber.open(normalized_path) as pdf:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                m = _TEACHER_CODE_RE.search(text)
                if m and m.group(1).strip() == teacher_code:
                    matching_indices.append(i)
    except FileNotFoundError:
        return None

    if not matching_indices:
        return None

    with pikepdf.open(normalized_path) as src:
        dst = pikepdf.new()
        for idx in matching_indices:
            dst.pages.append(src.pages[idx])
        buf = io.BytesIO()
        dst.save(buf)

    return buf.getvalue()
