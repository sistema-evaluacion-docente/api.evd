"""Tests for the messages the improvement-plan module sends."""

import datetime

import pytest

from api.utils import plan_links
from api.utils.plan_email import (
    close_result_label,
    director_title,
    manager_plan_url,
    plan_url,
    render_evidence_comment_for_director,
    render_evidence_comment_for_teacher,
    render_evidence_requested,
    render_evidence_reviewed,
    render_evidence_submitted,
    render_plan_closed,
    render_plan_created,
)


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


@pytest.fixture
def closed():
    """The mail a teacher gets when their plan is settled at the end."""

    return render_plan_closed(
        plan_id=42,
        plan_title="Plan de mejoramiento 2026-1",
        teacher_name="Ada Lovelace",
        teacher_email="ada@ufps.edu.co",
        director_name="Marco Antonio Adarme Jaimes",
        department_name="Departamento de Sistemas e Informática",
        result="CUMPLIDO",
        reason="Alcanzó la meta en las cuatro dimensiones.",
        period_code="2026-1",
    )


class TestPlanClosed:
    """The message that settles a plan."""

    def test_is_addressed_to_the_teacher(self, closed):
        assert closed.to == "ada@ufps.edu.co"
        assert "Ada Lovelace" in closed.html
        assert "Ada Lovelace" in closed.text

    def test_names_the_plan_and_says_it_is_a_closing(self, closed):
        assert "Plan de mejoramiento 2026-1" in closed.subject
        assert "Cierre" in closed.subject
        assert "Plan de mejoramiento 2026-1" in closed.html

    def test_states_the_verdict_where_it_cannot_be_missed(self, closed):
        """Test the result is the point of the message, not a footnote."""

        assert "Cumplido" in closed.html
        assert "Cumplido" in closed.text

    def test_carries_the_directors_observations_when_there_are_any(self, closed):
        assert "Alcanzó la meta en las cuatro dimensiones." in closed.html
        assert "Alcanzó la meta en las cuatro dimensiones." in closed.text

    def test_says_nothing_extra_when_the_director_left_no_reason(self):
        message = render_plan_closed(
            plan_id=7,
            plan_title="Plan",
            teacher_name="Ada",
            teacher_email="ada@ufps.edu.co",
            director_name="Marco",
            department_name="Departamento de Sistemas",
            result="CUMPLIDO",
        )

        assert "Observaciones" not in message.html
        assert "Observaciones" not in message.text

    def test_a_plan_not_met_reads_differently_from_one_that_was(self):
        """Test the two verdicts do not share one piece of boilerplate."""

        met = render_plan_closed(
            plan_id=7,
            plan_title="Plan",
            teacher_name="Ada",
            teacher_email="ada@ufps.edu.co",
            director_name="Marco",
            department_name="Departamento de Sistemas",
            result="CUMPLIDO",
        )
        unmet = render_plan_closed(
            plan_id=7,
            plan_title="Plan",
            teacher_name="Ada",
            teacher_email="ada@ufps.edu.co",
            director_name="Marco",
            department_name="Departamento de Sistemas",
            result="NO_CUMPLIDO",
        )

        assert "No cumplido" in unmet.html
        assert "Cumplido" in met.html
        assert met.html != unmet.html

    def test_carries_the_link_to_the_plan(self, closed):
        assert "/mis-planes/42" in closed.html
        assert "/mis-planes/42" in closed.text

    def test_signs_off_as_the_director_who_closed_it(self, closed):
        assert "Marco Antonio Adarme Jaimes" in closed.html
        assert "Director Departamento de Sistemas e Informática" in closed.html

    def test_ships_the_letterhead_like_every_other_message(self, closed):
        (header,) = closed.inline_images

        assert f"cid:{header.cid}" in closed.html
        assert "data:image" not in closed.html

    def test_always_carries_a_plain_text_twin(self, closed):
        assert closed.text.strip()
        assert "<" not in closed.text

    def test_escapes_a_reason_that_looks_like_markup(self):
        """Test the closing reason is data: the director types it into a form."""

        message = render_plan_closed(
            plan_id=7,
            plan_title="Plan",
            teacher_name="Ada",
            teacher_email="ada@ufps.edu.co",
            director_name="Marco",
            department_name="Departamento de Sistemas",
            result="NO_CUMPLIDO",
            reason="Faltó <b> evidencia & seguimiento",
        )

        assert "<b>" not in message.html
        assert "&lt;b&gt;" in message.html

    def test_leaves_the_period_out_when_there_is_none(self, closed):
        message = render_plan_closed(
            plan_id=7,
            plan_title="Plan",
            teacher_name="Ada",
            teacher_email="ada@ufps.edu.co",
            director_name="Marco",
            department_name="Departamento de Sistemas",
            result="CUMPLIDO",
        )

        assert "del periodo" not in message.html
        assert "2026-1" in closed.html

    def test_an_unknown_verdict_still_reads_as_a_closing(self):
        """Test a value the copy does not know about never leaks the raw enum."""

        assert close_result_label("ALGO_NUEVO") == "Cerrado"

    @pytest.mark.parametrize("result", ["CUMPLIDO", "NO_CUMPLIDO"])
    def test_renders_for_both_verdicts(self, result):
        """Test the only two verdicts a director can pick both build a message.

        The closing note used to be looked up with a default that named a
        verdict that no longer exists; ``dict.get`` evaluates that default on
        every call, so every closing mail raised ``KeyError`` and was swallowed
        by the best-effort ``except`` around the send. Nobody got a mail and
        nothing failed loudly.
        """

        message = render_plan_closed(
            plan_id=7,
            plan_title="Plan",
            teacher_name="Ada",
            teacher_email="ada@ufps.edu.co",
            director_name="Marco",
            department_name="Departamento de Sistemas",
            result=result,
        )

        assert close_result_label(result) in message.html
        assert message.text.strip()

    def test_leaves_no_empty_paragraph_when_the_verdict_has_no_note(self):
        """Test an unknown verdict drops the sentence instead of printing a hole."""

        message = render_plan_closed(
            plan_id=7,
            plan_title="Plan",
            teacher_name="Ada",
            teacher_email="ada@ufps.edu.co",
            director_name="Marco",
            department_name="Departamento de Sistemas",
            result="ALGO_NUEVO",
        )

        assert '<p style="margin:0 0 16px 0;"></p>' not in message.html


@pytest.fixture
def requested():
    """The mail a teacher gets when a deliverable is asked of them."""

    return render_evidence_requested(
        plan_id=42,
        plan_title="Plan de mejoramiento 2026-1",
        request_title="Listas de asistencia",
        request_description="Semanas 1 a 8",
        due_date=datetime.date(2026, 9, 30),
        teacher_name="Ada Lovelace",
        teacher_email="ada@ufps.edu.co",
        director_name="Marco Antonio Adarme Jaimes",
        department_name="Departamento de Sistemas e Informática",
    )


class TestEvidenceRequested:
    """What the teacher is asked for, and by when."""

    def test_is_addressed_to_the_teacher(self, requested):
        assert requested.to == "ada@ufps.edu.co"
        assert "profesor(a) Ada Lovelace" in requested.text

    def test_names_the_deliverable_and_its_deadline(self, requested):
        assert "Listas de asistencia" in requested.text
        assert "Semanas 1 a 8" in requested.text
        # A deadline nobody can read is a deadline nobody meets.
        assert "30/09/2026" in requested.text

    def test_leaves_the_deadline_out_when_there_is_none(self):
        message = render_evidence_requested(
            plan_id=42,
            plan_title="Plan",
            request_title="Listas",
            request_description=None,
            due_date=None,
            teacher_name="Ada",
            teacher_email="ada@ufps.edu.co",
            director_name="Marco",
            department_name=None,
        )

        assert "fecha límite" not in message.text

    def test_sends_the_teacher_to_their_own_screen(self, requested):
        # /planes/{id} is the director's, and answers a teacher with a page they
        # have no business on.
        assert plan_url(42) in requested.text
        assert plan_url(42) in requested.html

    def test_signs_off_as_the_director_who_asked(self, requested):
        assert "Marco Antonio Adarme Jaimes" in requested.html
        assert "Director Departamento de Sistemas e Informática" in requested.html

    def test_ships_the_letterhead_like_every_other_message(self, requested):
        assert len(requested.inline_images) == 1
        assert f"cid:{requested.inline_images[0].cid}" in requested.html

    def test_escapes_a_title_that_looks_like_markup(self):
        message = render_evidence_requested(
            plan_id=1,
            plan_title="Plan",
            request_title="<script>alert(1)</script>",
            request_description=None,
            due_date=None,
            teacher_name="Ada",
            teacher_email="ada@ufps.edu.co",
            director_name="Marco",
            department_name=None,
        )

        assert "<script>" not in message.html
        assert "&lt;script&gt;" in message.html


class TestEvidenceReviewed:
    """The verdict, and what the teacher has to do about it."""

    def _reviewed(self, *, approved, comment=None):
        return render_evidence_reviewed(
            plan_id=42,
            plan_title="Plan de mejoramiento 2026-1",
            approved=approved,
            comment=comment,
            teacher_name="Ada Lovelace",
            teacher_email="ada@ufps.edu.co",
            director_name="Marco",
            department_name=None,
        )

    def test_an_approval_says_so_in_the_subject(self):
        assert "aprobada" in self._reviewed(approved=True).subject.lower()

    def test_a_rejection_says_what_comes_next(self):
        message = self._reviewed(approved=False)

        assert "rechazada" in message.subject.lower()
        assert "Debe enviar una nueva" in message.text

    def test_carries_the_reviewer_own_words_when_there_are_any(self):
        message = self._reviewed(approved=False, comment="Falta la firma")

        assert "Falta la firma" in message.text
        assert "Observación del director" in message.text

    def test_says_nothing_extra_when_the_reviewer_left_no_comment(self):
        assert "Observación del director" not in self._reviewed(approved=True).text


class TestMessagesToTheDirector:
    """The other half of the loop, which the teacher sets off."""

    def test_a_submission_lands_on_the_screen_it_is_reviewed_from(self):
        message = render_evidence_submitted(
            plan_id=42,
            plan_title="Plan de mejoramiento 2026-1",
            teacher_name="Ada Lovelace",
            director_name="Marco",
            director_email="marco@ufps.edu.co",
        )

        assert message.to == "marco@ufps.edu.co"
        assert "director(a) Marco" in message.text
        assert manager_plan_url(42) in message.text

    def test_a_comment_carries_what_was_actually_said(self):
        message = render_evidence_comment_for_director(
            plan_id=42,
            plan_title="Plan",
            comment="¿Sirve así?",
            teacher_name="Ada Lovelace",
            director_name="Marco",
            director_email="marco@ufps.edu.co",
        )

        assert "¿Sirve así?" in message.text
        assert "Ada Lovelace" in message.subject

    def test_is_signed_by_the_platform_and_not_by_the_teacher(self):
        # The teacher did not write to the director; the system did, because
        # they uploaded something. Signing it as them would be a fiction.
        message = render_evidence_submitted(
            plan_id=42,
            plan_title="Plan",
            teacher_name="Ada Lovelace",
            director_name="Marco",
            director_email="marco@ufps.edu.co",
        )

        assert "Sistema de Evaluación Docente" in message.html
        assert "Director" not in message.html.split("Cordialmente")[1]

    def test_a_comment_the_other_way_round_goes_to_the_teacher(self):
        message = render_evidence_comment_for_teacher(
            plan_id=42,
            plan_title="Plan",
            comment="Revisa el formato",
            teacher_name="Ada Lovelace",
            teacher_email="ada@ufps.edu.co",
            director_name="Marco",
            department_name="Química",
        )

        assert message.to == "ada@ufps.edu.co"
        assert plan_url(42) in message.text
        assert "Director Departamento Química" in message.html
