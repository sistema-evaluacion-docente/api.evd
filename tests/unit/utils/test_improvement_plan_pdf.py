"""Tests for the renderer of the three official UFPS forms.

Pure "context in, bytes out". The PDF of record and the editable Word copy share
the same Jinja templates on purpose, so what is worth asserting is that they
cannot drift: same templates, same titles, and the only differences are the ones
Word needs — inlined logos and table borders as HTML attributes.
"""

import base64
import datetime

import pytest

from api.utils.improvement_plan_pdf import (
    FORMAT_TEMPLATES,
    FORMAT_TITLES,
    LOGOS,
    TEMPLATES_DIR,
    _date_es,
    _render_html,
    render_formato,
    render_formato_word,
)


def _context(**overrides) -> dict:
    context = {
        "plan": {"id": 7, "title": "Plan de mejoramiento"},
        "teacher_name": "Ada Lovelace",
        "aspects": [],
        "courses": [],
        "checkpoints": [],
    }
    context.update(overrides)
    return context


class TestDateEs:
    """The printed forms spell the date out in Spanish."""

    def test_spells_the_month_out(self):
        assert _date_es(datetime.date(2026, 9, 30)) == "30 de septiembre de 2026"

    def test_parses_an_iso_string(self):
        """Test a date that arrived as JSON is rendered, not printed raw."""

        assert _date_es("2026-01-05") == "5 de enero de 2026"

    def test_a_missing_date_prints_as_empty(self):
        """Test an unset date leaves a blank to fill in by hand, not a "None"."""

        assert _date_es(None) == ""
        assert _date_es("") == ""

    def test_a_string_that_is_not_a_date_is_left_alone(self):
        """Test free text a director typed survives instead of blowing up."""

        assert _date_es("por definir") == "por definir"

    def test_every_month_has_a_spanish_name(self):
        """Test the month table is complete — an off-by-one here prints wrong."""

        for month in range(1, 13):
            rendered = _date_es(datetime.date(2026, month, 1))
            assert rendered.startswith("1 de ")
            assert rendered.endswith(" de 2026")


class TestTemplateCatalogue:
    """Formato 1 has no template: it reaches the director already filled."""

    def test_only_the_two_generated_formats_are_listed(self):
        assert set(FORMAT_TEMPLATES) == {"FORMATO_2", "FORMATO_3"}

    def test_every_listed_format_has_a_title(self):
        assert set(FORMAT_TITLES) >= set(FORMAT_TEMPLATES)

    def test_every_template_file_exists(self):
        """Test a renamed template is caught here and not at signing time."""

        for filename in FORMAT_TEMPLATES.values():
            assert (TEMPLATES_DIR / filename).is_file()

    def test_every_logo_file_exists(self):
        """Test the letterhead images the Word copy inlines are really there."""

        for filename in LOGOS.values():
            assert (TEMPLATES_DIR / "assets" / filename).is_file()


class TestRenderHtml:
    """The one function both outputs go through."""

    @pytest.mark.parametrize("format_type", ["FORMATO_2", "FORMATO_3"])
    def test_renders_each_official_format(self, format_type):
        html = _render_html(format_type, _context(), word=False)

        assert FORMAT_TITLES[format_type] in html

    def test_an_unknown_format_is_rejected(self):
        """Test Formato 1 and typos raise instead of rendering an empty form."""

        with pytest.raises(ValueError):
            _render_html("FORMATO_1", _context(), word=False)

    def test_the_pdf_links_its_logos_relatively(self):
        """Test WeasyPrint resolves them against the templates directory."""

        html = _render_html("FORMATO_2", _context(), word=False)

        assert "assets/ufps-logo.png" in html
        assert "data:image/png;base64," not in html

    def test_the_word_copy_inlines_its_logos(self):
        """Test the editable copy travels as a single file.

        Word has no base URL to resolve a relative path against, so a linked
        logo would reach the director as a broken image.
        """

        html = _render_html("FORMATO_2", _context(), word=True)

        assert "data:image/png;base64," in html
        assert "assets/ufps-logo.png" not in html

    def test_the_word_copy_carries_table_borders_as_attributes(self):
        """Test the grid survives the import into a word processor.

        Word imports border attributes far more reliably than a stylesheet, and
        an official form without its grid is not the official form.
        """

        html = _render_html("FORMATO_3", _context(), word=True)

        assert 'border="1"' in html

    def test_the_pdf_leaves_the_table_attributes_out(self):
        """Test WeasyPrint takes the borders from the CSS instead."""

        html = _render_html("FORMATO_3", _context(), word=False)

        assert 'border="1"' not in html

    def test_the_context_reaches_the_template(self):
        html = _render_html("FORMATO_2", _context(), word=False)

        assert "Ada Lovelace" in html

    def test_escapes_what_a_director_typed(self):
        """Test autoescape is on: plan text is user input on a printed form."""

        html = _render_html(
            "FORMATO_2", _context(teacher_name="<script>alert(1)</script>"), word=False
        )

        assert "<script>alert(1)</script>" not in html
        assert "&lt;script&gt;" in html


class TestRenderFormatoWord:
    """The editable copy the director corrects before printing to sign."""

    def test_returns_utf8_bytes(self):
        """Test the Spanish of the form survives the encoding."""

        content = render_formato_word("FORMATO_2", _context())

        assert isinstance(content, bytes)
        assert "Ficha de acuerdo" in content.decode("utf-8")

    def test_is_the_same_document_as_the_pdf(self):
        """Test both outputs come from one template, so they cannot drift."""

        content = render_formato_word("FORMATO_3", _context()).decode("utf-8")

        assert FORMAT_TITLES["FORMATO_3"] in content

    def test_an_unknown_format_is_rejected(self):
        with pytest.raises(ValueError):
            render_formato_word("FORMATO_9", _context())

    def test_the_inlined_logo_is_valid_base64(self):
        """Test the data URI is a real image, not a truncated payload."""

        content = render_formato_word("FORMATO_2", _context()).decode("utf-8")
        payload = content.split("data:image/png;base64,")[1].split('"')[0]

        assert base64.b64decode(payload).startswith(b"\x89PNG")


class TestRenderFormato:
    """The PDF of record, the one that gets printed and signed."""

    @pytest.mark.parametrize("format_type", ["FORMATO_2", "FORMATO_3"])
    def test_produces_a_real_pdf(self, format_type):
        """Test WeasyPrint and its system libraries actually render the form.

        This is the only check that the Pango/HarfBuzz stack the Dockerfiles
        install is present: everything above it renders HTML just fine without
        it, and the failure only shows at the moment a director asks to print.
        """

        content = render_formato(format_type, _context())

        assert content.startswith(b"%PDF-")

    def test_an_unknown_format_is_rejected(self):
        with pytest.raises(ValueError):
            render_formato("FORMATO_1", _context())
