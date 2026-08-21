"""Tests for the messages the improvement-plan module sends."""

import pytest

from api.utils import plan_links
from api.utils.plan_email import director_title, plan_url, render_plan_created


@pytest.fixture
def message():
    """The mail a teacher gets when a plan is drawn up for them."""

    return render_plan_created(
        plan_id=42,
        plan_title="Plan de mejoramiento 2026-1",
        teacher_name="Ada Lovelace",
        teacher_email="ada@ufps.edu.co",
        director_name="Marco Antonio Adarme Jaimes",
        department_name="Departamento de Sistemas e Informática",
        period_code="2026-1",
    )


class TestDirectorTitle:
    """How the director signs off, given how the department is named."""

    def test_does_not_repeat_the_word_already_in_the_name(self):
        """Test departments are stored with "Departamento" already in them."""

        assert (
            director_title("Departamento de Sistemas e Informática")
            == "Director Departamento de Sistemas e Informática"
        )

    def test_adds_the_word_when_the_name_lacks_it(self):
        assert director_title("Química") == "Director Departamento Química"

    def test_falls_back_when_the_department_is_unknown(self):
        """Test a plan whose department could not be resolved still signs off."""

        assert director_title(None) == "Director de Departamento"
        assert director_title("   ") == "Director de Departamento"


class TestPlanUrl:
    """Where the link takes the teacher."""

    def test_points_at_the_teachers_own_route(self, monkeypatch):
        """Test /planes/{id} is the director's screen, not the teacher's."""

        monkeypatch.setattr(plan_links.config, "FRONTEND_URL", "https://evd.ufps.edu.co")

        assert plan_url(42) == "https://evd.ufps.edu.co/mis-planes/42"


class TestPlanCreated:
    """The message itself."""

    def test_is_addressed_to_the_teacher(self, message):
        assert message.to == "ada@ufps.edu.co"
        assert "Ada Lovelace" in message.html
        assert "Ada Lovelace" in message.text

    def test_names_the_plan_in_the_subject_and_the_body(self, message):
        assert "Plan de mejoramiento 2026-1" in message.subject
        assert "Plan de mejoramiento 2026-1" in message.html

    def test_carries_the_link_to_the_plan(self, message):
        assert "/mis-planes/42" in message.html
        assert "/mis-planes/42" in message.text

    def test_signs_off_as_the_director_who_drew_it_up(self, message):
        assert "Marco Antonio Adarme Jaimes" in message.html
        assert "Director Departamento de Sistemas e Informática" in message.html
        assert "Cúcuta,CO" in message.html

    def test_ships_the_letterhead_with_the_message(self, message):
        """Test the header travels as an attachment, not as a data: URI.

        Gmail and most webmail strip `data:` images, so the letterhead has to be
        referenced by Content-ID and carried along.
        """

        (header,) = message.inline_images

        assert f"cid:{header.cid}" in message.html
        assert "data:image" not in message.html
        assert header.content[:4] == b"\x89PNG"

    def test_always_carries_a_plain_text_twin(self, message):
        """Test clients that refuse HTML still get something readable."""

        assert message.text.strip()
        assert "<" not in message.text

    def test_escapes_a_title_that_looks_like_markup(self):
        """Test a plan title is data, never markup: it comes from a form."""

        message = render_plan_created(
            plan_id=7,
            plan_title="Metodología <b> & evaluación",
            teacher_name="Ada",
            teacher_email="ada@ufps.edu.co",
            director_name="Marco",
            department_name="Departamento de Sistemas",
            period_code=None,
        )

        assert "<b>" not in message.html
        assert "&lt;b&gt;" in message.html
        assert "&amp;" in message.html

    def test_leaves_the_period_out_when_there_is_none(self):
        """Test a plan without an origin period code reads as a sentence still."""

        message = render_plan_created(
            plan_id=7,
            plan_title="Plan",
            teacher_name="Ada",
            teacher_email="ada@ufps.edu.co",
            director_name="Marco",
            department_name="Departamento de Sistemas",
            period_code=None,
        )

        assert "del periodo" not in message.html
        assert "del periodo" not in message.text
