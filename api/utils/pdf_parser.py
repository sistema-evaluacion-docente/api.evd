"""
PDF parser for UFPS teacher evaluation documents.

Expects one PDF per department. Each page corresponds to one teacher block containing:
- Teacher code and name
- Contract type (TC, TP, HC, etc.)
- Score table: course code, course name, respondent count, 22 question scores, overall average
- Comments section grouped by academic group

Requires pikepdf to repair the PDF before reading (files are corrupted when downloaded
from the university server).
"""

import os
import re
import tempfile
from decimal import Decimal, InvalidOperation

import pdfplumber
import pikepdf

QUESTION_CODES = [f"{i:03d}" for i in range(1, 23)]

_PERIOD_MAP = {"primer": "1", "segundo": "2"}


def _load_nlp():
    """Load Spanish NER model for comment anonymization. Returns None if unavailable."""
    try:
        import spacy

        for model in ("es_core_news_lg", "es_core_news_sm"):
            try:
                return spacy.load(model, disable=["parser", "tagger", "lemmatizer"])
            except OSError:
                continue
    except ImportError:
        pass
    return None


def _to_decimal(raw: str) -> Decimal | None:
    try:
        return Decimal(raw.strip().replace(",", "."))
    except (InvalidOperation, AttributeError):
        return None


def _parse_period_code(text: str) -> str | None:
    """
    'Primer Semestre de 2025'  → '2025-1'
    'Segundo Semestre de 2025' → '2025-2'
    """
    match = re.search(
        r"(Primer|Segundo)\s+Semestre\s+de\s+(\d{4})", text, re.IGNORECASE
    )
    if not match:
        return None
    semester = _PERIOD_MAP[match.group(1).lower()]
    return f"{match.group(2)}-{semester}"


def _parse_department(text: str) -> tuple[str, str] | None:
    """Extract department code and name from '52 SISTEMAS E INFORMATICA'."""
    match = re.search(r"^\s*(\d{2})\s+([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ\s]+)$", text, re.MULTILINE)
    if not match:
        return None
    return match.group(1).strip(), match.group(2).strip()


def _parse_teacher_header(text: str) -> dict | None:
    """
    Extract teacher code, name, and contract type from a single line:
    '04041 ADARME JAIMES MARCO ANTONIO TC'
    """
    match = re.search(
        r"^\s*(\d{5,})\s+([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ ]+?)(?:\s+(TC|TP|HC|HORA\s+CATEDRA))?\s*$",
        text,
        re.MULTILINE,
    )
    if not match:
        return None

    return {
        "code": match.group(1).strip(),
        "name": match.group(2).strip(),
        "contract_type": match.group(3).strip() if match.group(3) else None,
    }


def _parse_score_table(tables: list) -> tuple[list[dict], Decimal | None]:
    """
    Parse the score table returned by pdfplumber.extract_tables().

    Row layout (26 columns):
      [course_code, course_name, enc, score_001, ..., score_022, group_average]

    Course code cell format: '1155304B01' (no spaces — concatenated in the PDF).

    The summary row (first cell empty) holds per-question averages across all groups;
    its last column is the teacher's overall average.

    Returns (groups, teacher_overall_average).
    """
    groups = []
    teacher_overall: Decimal | None = None
    course_code_re = re.compile(r"^(\d{7})([A-Z])(\d{2})$")

    for table in tables:
        for row in table:
            if not row:
                continue

            first = (row[0] or "").strip()

            # Summary row: empty first cell, contains teacher overall in last column
            if first == "" and len(row) > 25:
                teacher_overall = _to_decimal(row[25] or "")
                continue

            m = course_code_re.match(first)
            if not m:
                continue

            course_code = m.group(1)  # '1155304'
            group_letter = m.group(2)  # 'B'
            section = m.group(3)  # '01'
            course_name = (row[1] or "").strip()

            enc_raw = (row[2] or "").strip()
            respondent_count = int(enc_raw) if enc_raw.isdigit() else 0

            question_scores = {}
            for i, code in enumerate(QUESTION_CODES):
                col = 3 + i
                question_scores[code] = (
                    _to_decimal(row[col] or "") if col < len(row) else None
                )

            overall = _to_decimal(row[25] or "") if len(row) > 25 else None

            groups.append(
                {
                    "course_code": course_code,
                    "course_name": course_name,
                    "group": group_letter,
                    "section": section,
                    "respondent_count": respondent_count,
                    "overall_average": overall,
                    "question_scores": question_scores,
                    "comments": [],
                }
            )

    return groups, teacher_overall


def _extract_comments(text: str, nlp) -> dict[str, list[str]]:
    """
    Extract comments from the 'Observaciones realizadas' section.

    Group header format in that section: '115 5304  B  01  ESTRUCTURAS DE DATOS'
    Comment lines start with '- '.

    Returns dict keyed by '{course_code}_{group}_{section}', e.g. '1155304_B_01'.
    """
    lines = text.splitlines()

    start_idx = None
    for i, line in enumerate(lines):
        if "Observaciones realizadas" in line:
            start_idx = i + 1
            break

    if start_idx is None:
        return {}

    group_header = re.compile(
        r"^\s*(\d{3})\s+(\d{4})\s+([A-Z])\s+(\d{2})\s+", re.IGNORECASE
    )
    page_footer = re.compile(
        r"^\s*Pagina\s+\d+\s+Fecha\s+de\s+generacion", re.IGNORECASE
    )

    result: dict[str, list[str]] = {}
    current_key: str | None = None
    buffer = ""

    def flush():
        nonlocal buffer
        cleaned = re.sub(r"^\s*[-•]\s*", "", buffer).strip()
        cleaned = re.sub(r"\s+", " ", cleaned)
        if cleaned and current_key:
            if nlp:
                doc = nlp(cleaned)
                for ent in reversed([e for e in doc.ents if e.label_ == "PER"]):
                    cleaned = (
                        cleaned[: ent.start_char] + "@persona" + cleaned[ent.end_char :]
                    )
            result.setdefault(current_key, []).append(cleaned)
        buffer = ""

    for line in lines[start_idx:]:
        stripped = line.strip()

        if page_footer.match(line):
            flush()
            continue

        m = group_header.match(line)
        if m:
            flush()
            current_key = f"{m.group(1)}{m.group(2)}_{m.group(3)}_{m.group(4)}"
            continue

        if re.match(r"^\s*-\s+\S", line):
            flush()
            buffer = stripped
            continue

        if buffer and stripped and not stripped.startswith("-"):
            buffer += " " + stripped
            continue

        if not stripped:
            flush()

    flush()
    return result


def parse_pdf(file_bytes: bytes) -> dict:
    """
    Parse a UFPS teacher evaluation PDF.

    Args:
        file_bytes: Raw bytes of the PDF file.

    Returns:
        {
            "period_code": "2025-1",
            "department_code": "52",
            "department_name": "SISTEMAS E INFORMATICA",
            "teachers": [
                {
                    "code": "04041",
                    "name": "PROFESOR ABC",
                    "contract_type": "TC",
                    "overall_average": Decimal("4.85"),
                    "groups": [
                        {
                            "course_code": "1155304",
                            "course_name": "ESTRUCTURAS DE DATOS",
                            "group": "B",
                            "section": "01",
                            "respondent_count": 13,
                            "overall_average": Decimal("4.94"),
                            "question_scores": {"001": Decimal("5.00"), ...},
                            "comments": ["Excelente, se le entiende al explicar los temas"],
                        }
                    ],
                }
            ],
        }
    """
    nlp = _load_nlp()

    tmp_in = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    tmp_out_path = tmp_in.name + ".fixed.pdf"

    try:
        tmp_in.write(file_bytes)
        tmp_in.close()

        with pikepdf.open(tmp_in.name) as pdf_in:
            pdf_in.save(tmp_out_path)

        result: dict = {
            "period_code": None,
            "department_code": None,
            "department_name": None,
            "teachers": [],
        }

        with pdfplumber.open(tmp_out_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text(x_tolerance=3, y_tolerance=3) or ""
                if not text:
                    continue

                if not result["period_code"]:
                    result["period_code"] = _parse_period_code(text)

                if not result["department_code"]:
                    dept = _parse_department(text)
                    if dept:
                        result["department_code"], result["department_name"] = dept

                teacher = _parse_teacher_header(text)
                if not teacher:
                    continue

                tables = page.extract_tables(
                    {
                        "vertical_strategy": "lines",
                        "horizontal_strategy": "lines",
                    }
                )
                groups, teacher["overall_average"] = _parse_score_table(tables)

                comments_by_group = _extract_comments(text, nlp)
                for group in groups:
                    key = f"{group['course_code']}_{group['group']}_{group['section']}"
                    group["comments"] = comments_by_group.get(key, [])

                teacher["groups"] = groups
                result["teachers"].append(teacher)

        return result

    finally:
        if os.path.exists(tmp_in.name):
            os.remove(tmp_in.name)
        if os.path.exists(tmp_out_path):
            os.remove(tmp_out_path)
