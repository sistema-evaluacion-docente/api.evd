"""
Renderer for the three official UFPS improvement-plan forms.

Pure "context in, bytes out" module — the business logic that builds the context
lives in ``api/services/improvement_plan_document_service.py``. Same shape as
``api/utils/evaluation_excel_export.py``.

Two outputs share the same Jinja templates so they can never drift apart: the
PDF of record (WeasyPrint) and an editable Word copy, which is the very same
HTML served with Word's MIME type and the logos inlined as data URIs.
"""

import base64
import datetime
from functools import lru_cache
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup
from weasyprint import HTML

TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "templates" / "improvement_plans"
ASSETS_DIR = TEMPLATES_DIR / "assets"

# Public identifiers <-> template files.
#
# Formato 1 is not here and has no template: the caso reportado is written by
# the academic programme and reaches the director already filled, by email. He
# uploads that PDF; the platform only ever renders Formatos 2 and 3.
FORMAT_TEMPLATES = {
    "FORMATO_2": "formato_2.html",
    "FORMATO_3": "formato_3.html",
}

FORMAT_TITLES = {
    "FORMATO_2": "Ficha de acuerdo de mejoramiento y compromiso docente",
    "FORMATO_3": "Plan seguimiento y mejoramiento de la evaluación docente",
}

# Filenames of the letterhead images, relative to the templates directory.
LOGOS = {
    "ufps_logo_src": "ufps-logo.png",
    "acreditacion_logo_src": "acreditacion-logo.png",
}

_MONTHS_ES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]


def _date_es(value) -> str:
    """Render a date the way the printed forms expect, empty when missing."""

    if not value:
        return ""

    if isinstance(value, str):
        try:
            value = datetime.date.fromisoformat(value)
        except ValueError:
            return value

    return f"{value.day} de {_MONTHS_ES[value.month - 1]} de {value.year}"


@lru_cache(maxsize=8)
def _data_uri(filename: str) -> str:
    """Inline an asset, so the Word copy travels as a single file."""

    payload = base64.b64encode((ASSETS_DIR / filename).read_bytes()).decode()

    return f"data:image/png;base64,{payload}"


def _environment() -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    env.filters["date_es"] = _date_es

    return env


def _render_html(format_type: str, context: dict, *, word: bool) -> str:
    """Render one official form to HTML.

    WeasyPrint resolves the logos against ``base_url``; Word has no base URL to
    resolve against, so there they are embedded instead.
    """

    template_name = FORMAT_TEMPLATES.get(format_type)

    if not template_name:
        raise ValueError(f"Formato desconocido: {format_type}")

    logos = {
        key: _data_uri(filename) if word else f"assets/{filename}"
        for key, filename in LOGOS.items()
    }

    template = _environment().get_template(template_name)

    return template.render(
        title=FORMAT_TITLES[format_type],
        word=word,
        # Word processors import table borders from the HTML attributes far more
        # reliably than from a stylesheet; WeasyPrint takes them from the CSS.
        word_table_attrs=(
            Markup('border="1" cellspacing="0" cellpadding="4" width="100%"')
            if word
            else Markup("")
        ),
        **logos,
        **context,
    )


def render_formato(format_type: str, context: dict) -> bytes:
    """Render one official form to PDF bytes.

    ``base_url`` points at the templates directory so the relative ``assets/``
    logo paths resolve.
    """

    html = _render_html(format_type, context, word=False)

    return HTML(string=html, base_url=str(TEMPLATES_DIR)).write_pdf()


def render_formato_word(format_type: str, context: dict) -> bytes:
    """Render one official form as a Word-openable document.

    The acta is signed by hand and often needs a last-minute correction, so the
    director gets an editable copy. It is the PDF's own HTML with the logos
    inlined — Word reads it as a document and keeps the paper size and margins
    declared in the ``@page`` rule.
    """

    html = _render_html(format_type, context, word=True)

    return html.encode("utf-8")
