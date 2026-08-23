"""
Tests for reading the kind of program a UFPS evaluation PDF reports on, and
for combining the documents uploaded for a single evaluation.
"""

import pytest

from api.utils.pdf_parser import merge_parsed_evaluations, parse_pdf

QUESTION_SCORES = ["4.50"] * 22
HEADER_CELLS = (
    ["Codigo", "Nombre Materia", "Enc."] + [f"{i:03d}" for i in range(1, 23)] + [" "]
)


def _row(cells: list[str]) -> str:
    """Render a table row with the ruling lines the parser looks for."""

    return (
        "<tr>"
        + "".join(
            f'<td style="border:0.5pt solid #000; padding:1pt">{cell}</td>'
            for cell in cells
        )
        + "</tr>"
    )


def _render_evaluation_pdf(
    title: str,
    teacher: str = "04041 PROFESOR UNO TC",
    course_code: str = "1155304B01",
    comment: str = "Muy buen docente",
) -> bytes:
    """Render a one-teacher evaluation PDF laid out like the university's."""

    weasyprint = pytest.importorskip("weasyprint")

    score_row = [course_code, "ESTRUCTURAS DE DATOS", "13"] + QUESTION_SCORES + ["4.50"]
    summary_row = ["", "", ""] + QUESTION_SCORES + ["4.50"]

    html = f"""
    <style>
      @page {{ size: A4 landscape; margin: 10mm }}
      body {{ font-family: sans-serif; font-size: 7pt }}
      table {{ border-collapse: collapse; width: 100% }}
      td {{ font-size: 5pt }}
    </style>
    <p>UNIVERSIDAD FRANCISCO DE PAULA SANTANDER</p>
    <p>{title}</p>
    <p>52 SISTEMAS E INFORMATICA</p>
    <p>{teacher}</p>
    <table>{_row(HEADER_CELLS)}{_row(score_row)}{_row(summary_row)}</table>
    <p>Observaciones realizadas</p>
    <p>115 5304 B 01 ESTRUCTURAS DE DATOS</p>
    <p>- {comment}</p>
    """

    return weasyprint.HTML(string=html).write_pdf()


class TestParsePdfModality:
    """Test suite for the modality read out of the report title."""

    def test_reads_a_presencial_report(self):
        """Test the document and its groups are tagged as presencial."""

        parsed = parse_pdf(
            _render_evaluation_pdf(
                "Resultados de la Evaluación Docente - Programas Presenciales"
                " - Segundo Semestre de 2024"
            )
        )

        assert parsed["modality"] == "PRESENCIAL"
        assert parsed["period_code"] == "2024-2"
        assert [g["modality"] for g in parsed["teachers"][0]["groups"]] == [
            "PRESENCIAL"
        ]

    def test_reads_a_distancia_report(self):
        """Test the document and its groups are tagged as a distancia."""

        parsed = parse_pdf(
            _render_evaluation_pdf(
                "Resultados de la Evaluación Docente - Programas a Distancia"
                " - Segundo Semestre de 2024"
            )
        )

        assert parsed["modality"] == "DISTANCIA"
        assert [g["modality"] for g in parsed["teachers"][0]["groups"]] == ["DISTANCIA"]

    def test_leaves_the_modality_unset_when_the_title_omits_it(self):
        """Test a document that is not the university's report names no modality.

        The service refuses those uploads instead of guessing."""

        parsed = parse_pdf(
            _render_evaluation_pdf(
                "Resultados de la Evaluación Docente - Segundo Semestre de 2024"
            )
        )

        assert parsed["modality"] is None


class TestMergeParsedEvaluations:
    """Test suite for combining the PDFs uploaded for one evaluation."""

    @staticmethod
    def _document(modality, teachers):
        return {
            "period_code": "2024-2",
            "department_code": "52",
            "department_name": "SISTEMAS E INFORMATICA",
            "modality": modality,
            "teachers": teachers,
        }

    def test_a_single_document_is_returned_untouched(self):
        """Test uploading one PDF needs no merging."""

        document = self._document("PRESENCIAL", [{"code": "001", "groups": []}])

        assert merge_parsed_evaluations([document]) is document

    def test_a_teacher_in_both_documents_keeps_one_entry(self):
        """Test a docente teaching in both kinds of program is not duplicated."""

        presencial = self._document(
            "PRESENCIAL", [{"code": "001", "groups": [{"course_code": "A"}]}]
        )
        distancia = self._document(
            "DISTANCIA", [{"code": "001", "groups": [{"course_code": "B"}]}]
        )

        merged = merge_parsed_evaluations([presencial, distancia])

        assert len(merged["teachers"]) == 1
        assert [g["course_code"] for g in merged["teachers"][0]["groups"]] == ["A", "B"]

    def test_teachers_of_both_documents_are_kept(self):
        """Test every docente of either document makes it into the evaluation."""

        presencial = self._document("PRESENCIAL", [{"code": "001", "groups": []}])
        distancia = self._document("DISTANCIA", [{"code": "002", "groups": []}])

        merged = merge_parsed_evaluations([presencial, distancia])

        assert [t["code"] for t in merged["teachers"]] == ["001", "002"]
        assert merged["period_code"] == "2024-2"
        assert merged["department_code"] == "52"

    def test_merging_does_not_mutate_the_parsed_documents(self):
        """Test the documents can still be inspected after being merged."""

        presencial = self._document(
            "PRESENCIAL", [{"code": "001", "groups": [{"course_code": "A"}]}]
        )
        distancia = self._document(
            "DISTANCIA", [{"code": "001", "groups": [{"course_code": "B"}]}]
        )

        merge_parsed_evaluations([presencial, distancia])

        assert presencial["teachers"][0]["groups"] == [{"course_code": "A"}]
