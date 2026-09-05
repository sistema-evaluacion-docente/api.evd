"""Tests for pdf_extractor — pulling a teacher's pages out of an evaluation PDF.

Builds real PDFs with WeasyPrint (already a project dependency, used to render
the improvement plan PDFs) so pdfplumber/pikepdf run against real bytes
instead of mocks.
"""

import pytest

from api.utils.pdf_extractor import extract_teacher_pages

weasyprint = pytest.importorskip("weasyprint")


def _make_pdf(tmp_path, name: str, codes_and_names: list[tuple[str, str]]) -> str:
    """Render a PDF with one page per (teacher_code, teacher_name) pair."""

    pages_html = "".join(
        f'<section style="page-break-after: always;">'
        f"<p>{code} {name}</p></section>"
        for code, name in codes_and_names
    )
    html = f"<html><body>{pages_html}</body></html>"

    path = str(tmp_path / name)
    weasyprint.HTML(string=html).write_pdf(path)

    return path


class TestExtractTeacherPages:
    def test_returns_none_when_the_code_appears_nowhere(self, tmp_path):
        pdf_path = _make_pdf(tmp_path, "eval.pdf", [("10001", "ANA PEREZ")])

        result = extract_teacher_pages([pdf_path], "99999")

        assert result is None

    def test_extracts_the_matching_page(self, tmp_path):
        pdf_path = _make_pdf(
            tmp_path,
            "eval.pdf",
            [("10001", "ANA PEREZ"), ("20002", "CARLOS RUIZ")],
        )

        result = extract_teacher_pages([pdf_path], "10001")

        assert result is not None
        assert result.startswith(b"%PDF")

    def test_combines_pages_from_multiple_documents(self, tmp_path):
        """A teacher in both the presencial and distancia PDFs gets both pages."""

        presencial = _make_pdf(
            tmp_path, "presencial.pdf", [("10001", "ANA PEREZ")]
        )
        distancia = _make_pdf(tmp_path, "distancia.pdf", [("10001", "ANA PEREZ")])

        result = extract_teacher_pages([presencial, distancia], "10001")

        assert result is not None

    def test_ignores_a_document_that_does_not_exist(self, tmp_path):
        """A missing file among several paths does not blow up the whole report."""

        pdf_path = _make_pdf(tmp_path, "eval.pdf", [("10001", "ANA PEREZ")])
        missing_path = str(tmp_path / "missing.pdf")

        result = extract_teacher_pages([missing_path, pdf_path], "10001")

        assert result is not None

    def test_returns_none_when_every_document_is_missing(self, tmp_path):
        missing_path = str(tmp_path / "missing.pdf")

        result = extract_teacher_pages([missing_path], "10001")

        assert result is None
