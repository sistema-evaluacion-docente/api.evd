"""Tests for ImprovementPlansRepository layer."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sqlalchemy.exc import IntegrityError

from api.repositories.improvement_plans import ImprovementPlansRepository
from api.schemas.improvement_plan import (
    ImprovementPlanCaseReportUpsert,
    ImprovementPlanCheckpointUpdate,
    ImprovementPlanCreate,
)
from api.utils.dimensions import ASPECT_NUMBERS, DIMENSION_MAP


@pytest.fixture
def repo(mock_db):
    """Create repository instance with mocked DB."""

    return ImprovementPlansRepository(mock_db)


class TestGetDepartmentContext:
    """Header data the creation page prefills the official forms with."""

    @pytest.fixture
    def mock_query(self, mock_db):
        """Mock the chained SQLAlchemy query the method builds."""

        query = MagicMock()
        mock_db.query.return_value = query
        query.select_from.return_value = query
        query.outerjoin.return_value = query
        query.filter.return_value = query
        return query

    def test_returns_department_and_faculty_names(self, repo, mock_query):
        """Test the department is joined all the way up to its faculty."""

        row = MagicMock()
        row.department_name = "Departamento de Sistemas"
        row.faculty_name = "Ingeniería"
        mock_query.first.return_value = row

        result = repo.get_department_context(3)

        assert result == {
            "department_name": "Departamento de Sistemas",
            "faculty_name": "Ingeniería",
        }

    def test_returns_empty_context_when_the_department_is_unknown(self, repo, mock_query):
        """Test a missing department answers with nulls, not an exception.

        The form falls back to what the director types, so a department without
        a row must not take the whole candidates response down with it.
        """

        mock_query.first.return_value = None

        result = repo.get_department_context(999)

        assert result == {"department_name": None, "faculty_name": None}


class TestNextPeriodCode:
    """The origin period decides which one verifies the plan."""

    def test_first_semester_is_verified_by_the_second(self, repo):
        """Test a plan born in 2025-1 is judged by 2025-2."""

        assert repo._next_period_code("2025-1") == "2025-2"

    def test_second_semester_rolls_into_the_next_year(self, repo):
        """Test the year advances instead of producing a '2025-3'."""

        assert repo._next_period_code("2025-2") == "2026-1"

    def test_a_code_that_is_not_a_period_answers_none(self, repo):
        """Test a malformed code is not guessed at.

        A wrong guess here would point the verification at a real but unrelated
        period, so there is nothing to answer but ``None``.
        """

        assert repo._next_period_code("2025") is None


class TestTeacherLookups:
    """The teacher/user round trip every ownership check goes through."""

    def test_get_teacher_user_id_returns_the_linked_user(self, repo, mock_db):
        """Test the user id behind a teacher is unwrapped from the row."""

        mock_db.query.return_value.filter.return_value.first.return_value = (42,)

        assert repo.get_teacher_user_id(7) == 42

    def test_get_teacher_user_id_without_an_account_answers_none(self, repo, mock_db):
        """Test a teacher imported from a PDF has no user to point at."""

        mock_db.query.return_value.filter.return_value.first.return_value = None

        assert repo.get_teacher_user_id(7) is None

    def test_get_teacher_by_user_id_returns_the_teacher_row(self, repo, mock_db):
        """Test the reverse lookup the teacher's own listing keys off."""

        teacher = MagicMock()
        mock_db.query.return_value.filter.return_value.first.return_value = teacher

        assert repo.get_teacher_by_user_id(3) is teacher

    def test_get_teacher_department_id_unwraps_the_row(self, repo, mock_db):
        """Test the department that scopes a director's access."""

        mock_db.query.return_value.filter.return_value.first.return_value = (10,)

        assert repo.get_teacher_department_id(7) == 10

    def test_get_teacher_department_id_when_missing(self, repo, mock_db):
        """Test an unknown teacher has no department, not a crash."""

        mock_db.query.return_value.filter.return_value.first.return_value = None

        assert repo.get_teacher_department_id(7) is None


class TestDirectorLookups:
    """Who to ring on the other side of the evidence loop."""

    def test_user_id_without_a_department_never_queries(self, repo, mock_db):
        """Test a plan with no department short-circuits before the DB.

        An ADMIN has ``department_id`` ``None``; querying with it would match
        the first inactive director row instead of answering "nobody".
        """

        assert repo.get_department_director_user_id(None) is None
        mock_db.query.assert_not_called()

    def test_user_id_returns_the_active_director(self, repo, mock_db):
        """Test the active director's user id is unwrapped."""

        mock_db.query.return_value.filter.return_value.first.return_value = (9,)

        assert repo.get_department_director_user_id(10) == 9

    def test_user_id_when_the_department_has_no_director(self, repo, mock_db):
        """Test a department between directors answers None."""

        mock_db.query.return_value.filter.return_value.first.return_value = None

        assert repo.get_department_director_user_id(10) is None

    def test_contact_without_a_department_never_queries(self, repo, mock_db):
        """Test the e-mail twin short-circuits the same way."""

        assert repo.get_department_director_contact(None) is None
        mock_db.query.assert_not_called()

    def test_contact_returns_name_and_address(self, repo, mock_db):
        """Test an e-mail needs more than the id the bell needs."""

        # ``name`` is a MagicMock constructor kwarg, so it has to be set after.
        row = MagicMock(user_id=9, email="dir@ufps.edu.co")
        row.name = "Directora"
        query = mock_db.query.return_value
        query.select_from.return_value.join.return_value.filter.return_value.first.return_value = row

        assert repo.get_department_director_contact(10) == {
            "user_id": 9,
            "name": "Directora",
            "email": "dir@ufps.edu.co",
        }


class TestTeacherContact:
    """The address a plan notification is written to."""

    def test_returns_the_linked_account(self, repo, mock_db):
        """Test the teacher's user row becomes a contact dict."""

        row = MagicMock(user_id=5, email="doc@ufps.edu.co")
        row.name = "Docente"
        query = mock_db.query.return_value
        query.select_from.return_value.join.return_value.filter.return_value.first.return_value = row

        assert repo.get_teacher_contact(7) == {
            "user_id": 5,
            "name": "Docente",
            "email": "doc@ufps.edu.co",
        }

    def test_a_teacher_without_an_account_answers_none(self, repo, mock_db):
        """Test "nowhere to write to" is distinguishable from a failure.

        Teachers imported from an evaluation never signed in; the caller has to
        be able to skip the e-mail instead of treating it as an error.
        """

        query = mock_db.query.return_value
        query.select_from.return_value.join.return_value.filter.return_value.first.return_value = None

        assert repo.get_teacher_contact(7) is None


class TestTeacherContext:
    """Header data the three official forms print."""

    @pytest.fixture
    def mock_query(self, mock_db):
        query = MagicMock()
        mock_db.query.return_value = query
        query.select_from.return_value = query
        query.outerjoin.return_value = query
        query.filter.return_value = query
        return query

    def test_returns_code_department_and_faculty(self, repo, mock_query):
        """Test the teacher is joined all the way up to the faculty."""

        row = MagicMock(
            institutional_code="1150",
            department_name="Sistemas",
            faculty_name="Ingeniería",
        )
        mock_query.first.return_value = row

        assert repo.get_teacher_context(7) == {
            "code": "1150",
            "department_name": "Sistemas",
            "faculty_name": "Ingeniería",
        }

    def test_an_unknown_teacher_answers_nulls(self, repo, mock_query):
        """Test the form falls back to what the director types."""

        mock_query.first.return_value = None

        assert repo.get_teacher_context(999) == {
            "code": None,
            "department_name": None,
            "faculty_name": None,
        }


class TestGetTeacherCourses:
    """The asignaturas the creation page prefills the courses table with."""

    async def test_maps_every_group_with_its_carrera(self, repo, mock_db):
        """Test the program joined off the course code rides along."""

        row = MagicMock(
            id=3,
            course_name="Cálculo I",
            course_code="115201",
            group_name="A",
            program_name="Ingeniería de Sistemas",
        )
        query = mock_db.query.return_value
        query.outerjoin.return_value = query
        query.filter.return_value = query
        query.order_by.return_value = query
        query.all.return_value = [row]

        result = await repo.get_teacher_courses(7, 1)

        assert result == [
            {
                "academic_group_id": 3,
                "course_name": "Cálculo I",
                "course_code": "115201",
                "group_name": "A",
                "program_name": "Ingeniería de Sistemas",
            }
        ]


class TestHasPlanFor:
    """The duplicate-plan guard: one plan per teacher and origin period."""

    async def test_true_when_a_plan_already_exists(self, repo, mock_db):
        """Test an existing row blocks a second plan for the same period."""

        mock_db.query.return_value.filter.return_value.first.return_value = (1,)

        assert await repo.has_plan_for(7, 1) is True

    async def test_false_when_the_period_is_free(self, repo, mock_db):
        """Test nothing found means the plan may be created."""

        mock_db.query.return_value.filter.return_value.first.return_value = None

        assert await repo.has_plan_for(7, 1) is False


class TestQuestionAverages:
    """Per-teacher, per-question averages, resolved in one query."""

    def test_no_teachers_short_circuits_before_the_query(self, repo, mock_db):
        """Test an empty candidate list never reaches the database.

        ``IN ()`` is not valid SQL, and the answer is known without asking.
        """

        assert repo.question_averages([], 1) == {}
        mock_db.query.assert_not_called()

    def test_groups_rows_per_teacher_and_rounds(self, repo, mock_db):
        """Test each teacher gets a dict keyed by question code."""

        rows = [
            MagicMock(teacher_id=7, question_code="P1", avg_score=3.456),
            MagicMock(teacher_id=7, question_code="P2", avg_score=4.0),
            MagicMock(teacher_id=8, question_code="P1", avg_score=2.5),
        ]
        query = mock_db.query.return_value
        query.join.return_value = query
        query.filter.return_value = query
        query.group_by.return_value = query
        query.all.return_value = rows

        assert repo.question_averages([7, 8], 1) == {
            7: {"P1": 3.46, "P2": 4.0},
            8: {"P1": 2.5},
        }


class TestDimensionAverage:
    """A dimension is the mean of the questions that make it up."""

    def test_averages_only_the_codes_it_was_given(self, repo):
        """Test questions outside the dimension are left out."""

        averages = {"P1": 3.0, "P2": 4.0, "P9": 1.0}

        assert repo.dimension_average(averages, ["P1", "P2"]) == 3.5

    def test_ignores_codes_the_teacher_has_no_score_for(self, repo):
        """Test a missing question does not drag the mean to zero."""

        assert repo.dimension_average({"P1": 3.0}, ["P1", "P2"]) == 3.0

    def test_answers_none_when_nothing_matches(self, repo):
        """Test an unscored dimension is None, not 0.0.

        A 0.0 would read as the worst possible score and raise an indicator the
        teacher was never evaluated on.
        """

        assert repo.dimension_average({"P1": 3.0}, ["P7", "P8"]) is None


def _make_plan(plan_id=1, items=None, case_report=None, checkpoints=None):
    """A loaded plan with the handful of attributes the mutations touch."""

    plan = MagicMock()
    plan.id = plan_id
    plan.items = items if items is not None else []
    plan.evidences = []
    plan.case_report = case_report
    plan.checkpoints = checkpoints if checkpoints is not None else []
    return plan


@pytest.fixture
def loaded(repo):
    """Stub ``_load``/``_enrich`` so the mutations can be read on their own.

    Both are exercised through the listing tests; here they would only drag the
    whole serializer and its relationship graph into a state assertion.
    """

    plan = _make_plan()
    repo._load = MagicMock(return_value=plan)
    repo._enrich = MagicMock(side_effect=lambda p: {"id": p.id})
    return plan


class TestGetAll:
    """The shared listing every plan directory is a narrowing of."""

    @pytest.fixture
    def query(self, repo, mock_db):
        query = MagicMock()
        mock_db.query.return_value = query
        query.filter.return_value = query
        query.join.return_value = query
        query.options.return_value = query
        query.order_by.return_value = query
        query.offset.return_value = query
        query.limit.return_value = query
        repo._enrich_many = MagicMock(side_effect=lambda plans: [{"id": p.id} for p in plans])
        return query

    async def test_paginates_and_reports_the_page_count(self, repo, query):
        """Test ``pages`` rounds up so a partial last page still counts."""

        query.count.return_value = 25
        query.all.return_value = [_make_plan(1)]

        result = await repo.get_all(page=2, limit=10)

        assert result["total"] == 25
        assert result["pages"] == 3
        assert result["page"] == 2
        assert result["limit"] == 10
        assert result["items"] == [{"id": 1}]
        query.offset.assert_called_once_with(10)
        query.limit.assert_called_once_with(10)

    async def test_no_results_report_zero_pages(self, repo, query):
        """Test an empty listing is 0 pages, not 1.

        The front end reads ``pages`` to draw the pager; a 1 there offers a page
        that holds nothing.
        """

        query.count.return_value = 0
        query.all.return_value = []

        result = await repo.get_all()

        assert result["pages"] == 0
        assert result["items"] == []

    async def test_a_search_term_joins_the_teachers_name(self, repo, query):
        """Test the search reaches the teacher's user row, not just the title.

        A director looks a plan up by who it is about far more often than by the
        title they typed months ago.
        """

        query.count.return_value = 0
        query.all.return_value = []

        await repo.get_all(search="  perez  ")

        assert query.join.call_count == 2

    async def test_without_filters_nothing_is_narrowed(self, repo, query):
        """Test an unfiltered listing adds no WHERE of its own."""

        query.count.return_value = 0
        query.all.return_value = []

        await repo.get_all()

        query.filter.assert_not_called()


class TestGetByIdAndDelete:
    """Single-plan read and the cascading delete."""

    async def test_get_by_id_returns_none_when_missing(self, repo):
        """Test the route turns this None into its 404."""

        repo._load = MagicMock(return_value=None)

        assert await repo.get_by_id(99) is None

    async def test_delete_removes_the_plan(self, repo, mock_db):
        """Test the row is deleted and the transaction committed."""

        plan = _make_plan()
        mock_db.query.return_value.filter.return_value.first.return_value = plan

        assert await repo.delete(1) is True
        mock_db.delete.assert_called_once_with(plan)
        mock_db.commit.assert_called_once()

    async def test_delete_of_a_missing_plan_commits_nothing(self, repo, mock_db):
        """Test a plan that is not there is False, not an empty commit."""

        mock_db.query.return_value.filter.return_value.first.return_value = None

        assert await repo.delete(99) is False
        mock_db.delete.assert_not_called()
        mock_db.commit.assert_not_called()


class TestSetActaStatus:
    """The acta's own lifecycle: BORRADOR / CERRADA / FIRMADA."""

    async def test_closing_stamps_who_froze_it_and_when(self, repo, loaded):
        """Test CERRADA records the trace of the freeze."""

        await repo.set_acta_status(1, "CERRADA", closed_by=2)

        assert loaded.acta_status == "CERRADA"
        assert loaded.acta_closed_by == 2
        assert loaded.acta_closed_at is not None

    async def test_signing_stamps_the_trace_too(self, repo, loaded):
        """Test an acta going straight to FIRMADA still records the freeze.

        The scan often lands without a CERRADA in between; skipping the stamp
        there would lose who agreed to the plan and when.
        """

        await repo.set_acta_status(1, "FIRMADA", closed_by=2)

        assert loaded.acta_closed_by == 2
        assert loaded.acta_closed_at is not None

    async def test_reopening_clears_the_trace(self, repo, loaded):
        """Test BORRADOR wipes the stamp so a reopened acta reads as open."""

        await repo.set_acta_status(1, "BORRADOR", closed_by=2)

        assert loaded.acta_status == "BORRADOR"
        assert loaded.acta_closed_at is None
        assert loaded.acta_closed_by is None

    async def test_a_missing_plan_answers_none(self, repo):
        """Test there is no acta to move on a plan that is not there."""

        repo._load = MagicMock(return_value=None)

        assert await repo.set_acta_status(99, "CERRADA") is None


class TestClose:
    """Closing the plan itself, which is a different thing from the acta."""

    async def test_cumplido_maps_to_the_fulfilled_status(self, repo, loaded):
        """Test the result the director signs becomes the plan status."""

        await repo.close(1, "CUMPLIDO", reason="Metas alcanzadas")

        assert loaded.status == "CERRADO_CUMPLIDO"
        assert loaded.close_reason == "Metas alcanzadas"
        assert loaded.closed_at is not None

    async def test_no_cumplido_maps_to_the_unfulfilled_status(self, repo, loaded):
        """Test the other half of the mapping."""

        await repo.close(1, "NO_CUMPLIDO")

        assert loaded.status == "CERRADO_NO_CUMPLIDO"
        assert loaded.close_reason is None

    async def test_a_missing_plan_answers_none(self, repo):
        """Test nothing to close means None, not a stray commit."""

        repo._load = MagicMock(return_value=None)

        assert await repo.close(99, "CUMPLIDO") is None


class TestEvidences:
    """Files hung off the plan, optionally tied to one compromiso."""

    async def test_an_item_from_another_plan_is_rejected(self, repo, loaded):
        """Test evidence cannot be filed under a compromiso of another plan.

        The item id arrives from the client; without this the file would attach
        to a plan the uploader may not even be allowed to see.
        """

        loaded.items = [MagicMock(id=5)]

        with pytest.raises(ValueError):
            await repo.add_evidence(1, "/tmp/e.pdf", item_id=99)

    async def test_evidence_is_appended_to_the_plan(self, repo, loaded, mock_db):
        """Test the file lands on the plan and the transaction commits."""

        loaded.items = [MagicMock(id=5)]

        await repo.add_evidence(1, "/tmp/e.pdf", description="  Rúbrica ", item_id=5)

        assert len(loaded.evidences) == 1
        assert loaded.evidences[0].description == "Rúbrica"
        mock_db.commit.assert_called_once()

    async def test_a_blank_description_is_stored_as_none(self, repo, loaded):
        """Test whitespace is not kept as if the teacher had written something."""

        await repo.add_evidence(1, "/tmp/e.pdf", description="   ")

        assert loaded.evidences[0].description is None

    async def test_delete_hands_back_the_file_to_unlink(self, repo, mock_db):
        """Test the caller gets the path so the file leaves the disk too.

        Dropping the row alone would leave the PDF orphaned under ``uploads/``.
        """

        evidence = MagicMock(file_url="/tmp/e.pdf")
        mock_db.query.return_value.filter.return_value.first.return_value = evidence
        repo._load = MagicMock(return_value=_make_plan())
        repo._enrich = MagicMock(return_value={"id": 1})

        result = await repo.delete_evidence(1, 3)

        assert result == {"plan": {"id": 1}, "file_url": "/tmp/e.pdf"}
        mock_db.delete.assert_called_once_with(evidence)

    async def test_deleting_an_evidence_of_another_plan_answers_none(
        self, repo, mock_db
    ):
        """Test the plan id scopes the lookup, so a foreign id finds nothing."""

        mock_db.query.return_value.filter.return_value.first.return_value = None

        assert await repo.delete_evidence(1, 3) is None
        mock_db.delete.assert_not_called()


class TestCheckpoints:
    """The two formal seguimientos of the Formato 3 matrix."""

    async def test_get_checkpoint_is_scoped_to_the_plan(self, repo, mock_db):
        """Test a checkpoint belonging elsewhere is not returned.

        Both ids come from the URL; filtering by the checkpoint alone would let
        a director edit the seguimiento of a plan in another department.
        """

        mock_db.query.return_value.filter.return_value.first.return_value = None

        assert repo.get_checkpoint(1, 99) is None

    async def test_updating_a_foreign_checkpoint_answers_none(self, repo):
        """Test the scoped lookup is what the update goes through."""

        repo.get_checkpoint = MagicMock(return_value=None)

        result = await repo.update_checkpoint(
            1, 99, ImprovementPlanCheckpointUpdate(notes="hola")
        )

        assert result is None

    async def test_completing_a_seguimiento_stamps_the_date(self, repo, loaded):
        """Test COMPLETADO records when the follow-up actually happened."""

        checkpoint = MagicMock(completed_at=None, aspect_notes=[])
        repo.get_checkpoint = MagicMock(return_value=checkpoint)

        await repo.update_checkpoint(
            1, 2, ImprovementPlanCheckpointUpdate(status="COMPLETADO")
        )

        assert checkpoint.completed_at is not None

    async def test_an_already_completed_seguimiento_keeps_its_date(self, repo, loaded):
        """Test re-saving a completed follow-up does not move its date.

        The date is when the meeting happened; editing a note months later must
        not rewrite it.
        """

        original = datetime(2025, 3, 1, tzinfo=timezone.utc)
        checkpoint = MagicMock(completed_at=original, aspect_notes=[])
        repo.get_checkpoint = MagicMock(return_value=checkpoint)

        await repo.update_checkpoint(
            1, 2, ImprovementPlanCheckpointUpdate(status="COMPLETADO", notes="Ajuste")
        )

        assert checkpoint.completed_at == original

    async def test_an_existing_aspect_note_is_updated_in_place(self, repo, loaded):
        """Test a cell of the matrix is edited, not duplicated."""

        note = MagicMock(aspect=1, note="Antes")
        checkpoint = MagicMock(completed_at=None, aspect_notes=[note])
        repo.get_checkpoint = MagicMock(return_value=checkpoint)

        await repo.update_checkpoint(
            1,
            2,
            ImprovementPlanCheckpointUpdate(
                aspect_notes=[{"aspect": 1, "note": "Después"}]
            ),
        )

        assert len(checkpoint.aspect_notes) == 1
        assert note.note == "Después"

    async def test_a_new_aspect_note_is_appended(self, repo, loaded):
        """Test an aspect with nothing written yet gets its own row."""

        checkpoint = MagicMock(completed_at=None, aspect_notes=[])
        repo.get_checkpoint = MagicMock(return_value=checkpoint)

        await repo.update_checkpoint(
            1,
            2,
            ImprovementPlanCheckpointUpdate(
                aspect_notes=[{"aspect": 5, "note": "Observaciones"}]
            ),
        )

        assert len(checkpoint.aspect_notes) == 1
        assert checkpoint.aspect_notes[0].aspect == 5
        assert checkpoint.aspect_notes[0].note == "Observaciones"

    async def test_omitting_aspect_notes_leaves_them_alone(self, repo, loaded):
        """Test a partial update does not wipe the matrix.

        ``aspect_notes`` is popped out of the payload precisely so a save that
        only touches ``notes`` cannot clear the cells.
        """

        note = MagicMock(aspect=1, note="Intacta")
        checkpoint = MagicMock(completed_at=None, aspect_notes=[note])
        repo.get_checkpoint = MagicMock(return_value=checkpoint)

        await repo.update_checkpoint(
            1, 2, ImprovementPlanCheckpointUpdate(notes="Solo la nota general")
        )

        assert checkpoint.aspect_notes == [note]
        assert note.note == "Intacta"


class TestUpsertCaseReport:
    """Formato 1 — the complaint that originated the plan."""

    async def test_creates_the_report_when_the_plan_has_none(self, repo, loaded):
        """Test the first save attaches a report to the plan."""

        loaded.case_report = None

        await repo.upsert_case_report(
            1,
            ImprovementPlanCaseReportUpsert(complaint="Llega tarde"),
            reported_by=2,
        )

        assert loaded.case_report is not None
        assert loaded.case_report.complaint == "Llega tarde"
        assert loaded.case_report.reported_by == 2

    async def test_updates_the_existing_report(self, repo, loaded):
        """Test a second save edits the report instead of replacing it."""

        existing = MagicMock(reported_by=2)
        loaded.case_report = existing

        await repo.upsert_case_report(
            1, ImprovementPlanCaseReportUpsert(observations="Revisado")
        )

        assert loaded.case_report is existing
        assert existing.observations == "Revisado"

    async def test_an_omitted_field_is_left_untouched(self, repo, loaded):
        """Test a partial upsert does not blank out what it did not send."""

        existing = MagicMock(reported_by=2)
        existing.complaint = "Original"
        loaded.case_report = existing

        await repo.upsert_case_report(
            1, ImprovementPlanCaseReportUpsert(observations="Nueva")
        )

        assert existing.complaint == "Original"

    async def test_a_missing_plan_answers_none(self, repo):
        """Test there is no report to upsert on a plan that is not there."""

        repo._load = MagicMock(return_value=None)

        result = await repo.upsert_case_report(
            99, ImprovementPlanCaseReportUpsert(complaint="x")
        )

        assert result is None


class TestCreate:
    """Drawing a plan up: its scope, its verification period and its matrix."""

    @pytest.fixture
    def created(self, repo, mock_db):
        """Capture the plan handed to the session instead of enriching it."""

        repo._enrich = MagicMock(side_effect=lambda p: {"id": p.id})
        mock_db.query.return_value.filter.return_value.first.return_value = MagicMock(
            department_id=10
        )
        return mock_db

    def _payload(self, **overrides):
        data = {
            "teacher_id": 55,
            "origin_period_id": 1,
            "title": "Plan de mejoramiento",
        }
        data.update(overrides)
        return ImprovementPlanCreate(**data)

    async def test_the_department_comes_from_the_teacher(self, repo, created):
        """Test the plan is scoped by where the teacher is attached.

        Taking it from the payload would let a director file a plan under a
        department that is not theirs and then read it back through the scoped
        listing.
        """

        await repo.create(self._payload())

        plan = created.add.call_args[0][0]
        assert plan.department_id == 10

    async def test_a_teacher_without_a_department_leaves_it_unset(self, repo, mock_db):
        """Test an unknown teacher does not crash the creation."""

        repo._enrich = MagicMock(return_value={})
        mock_db.query.return_value.filter.return_value.first.return_value = None

        await repo.create(self._payload())

        assert mock_db.add.call_args[0][0].department_id is None

    async def test_the_verification_period_defaults_to_the_next_one(
        self, repo, created
    ):
        """Test the plan is judged by the semester after the one that caused it.

        That lag is the whole design: the notes that prove the improvement do
        not exist yet when the acta is signed.
        """

        repo._period_code = MagicMock(return_value="2025-1")
        repo._period_by_code = MagicMock(return_value=MagicMock(id=2))

        await repo.create(self._payload())

        repo._period_by_code.assert_called_once_with("2025-2")
        assert created.add.call_args[0][0].verification_period_id == 2

    async def test_an_explicit_verification_period_is_respected(self, repo, created):
        """Test a director who picked a period is not overridden."""

        repo._period_by_code = MagicMock()

        await repo.create(self._payload(verification_period_id=9))

        assert created.add.call_args[0][0].verification_period_id == 9
        repo._period_by_code.assert_not_called()

    async def test_an_unregistered_next_period_leaves_it_unset(self, repo, created):
        """Test a period the registry has not opened yet is left for later."""

        repo._period_code = MagicMock(return_value="2025-1")
        repo._period_by_code = MagicMock(return_value=None)

        await repo.create(self._payload())

        assert created.add.call_args[0][0].verification_period_id is None

    async def test_both_seguimientos_are_created_with_the_whole_matrix(
        self, repo, created
    ):
        """Test the Formato 3 matrix always renders complete.

        Creating the cells on demand would print a follow-up form with missing
        rows the director cannot fill in.
        """

        await repo.create(self._payload())

        plan = created.add.call_args[0][0]
        assert [c.stage for c in plan.checkpoints] == [
            "PRIMER_SEGUIMIENTO",
            "SEGUNDO_SEGUIMIENTO",
        ]
        for checkpoint in plan.checkpoints:
            assert checkpoint.status == "PENDIENTE"
            assert [n.aspect for n in checkpoint.aspect_notes] == ASPECT_NUMBERS

    async def test_a_new_plan_starts_in_seguimiento_with_a_draft_acta(
        self, repo, created
    ):
        """Test the plan and its acta start in their own opening states."""

        await repo.create(self._payload())

        plan = created.add.call_args[0][0]
        assert plan.status == "EN_SEGUIMIENTO"
        assert plan.acta_status == "BORRADOR"

    async def test_items_keep_the_order_they_were_sent_in(self, repo, created):
        """Test the compromisos print in the order the director wrote them."""

        await repo.create(
            self._payload(
                items=[
                    {"description": "Primero"},
                    {"description": "Segundo"},
                ]
            )
        )

        plan = created.add.call_args[0][0]
        assert [i.order for i in plan.items] == [0, 1]

    async def test_an_items_aspect_is_derived_from_its_indicator(self, repo, created):
        """Test a compromiso lands under the right section of the form.

        The director picks an indicator, not a section; deriving the aspect is
        what keeps the printed form organised without asking twice.
        """

        await repo.create(
            self._payload(
                items=[
                    {
                        "description": "Entregar a tiempo",
                        "target_type": "QUESTION",
                        "target_ref": "017",
                    }
                ]
            )
        )

        assert created.add.call_args[0][0].items[0].aspect == 3

    async def test_an_explicit_aspect_wins_over_the_derived_one(self, repo, created):
        """Test the director can place a compromiso by hand."""

        await repo.create(
            self._payload(
                items=[
                    {
                        "description": "Entregar a tiempo",
                        "target_type": "QUESTION",
                        "target_ref": "017",
                        "aspect": 5,
                    }
                ]
            )
        )

        assert created.add.call_args[0][0].items[0].aspect == 5

    async def test_a_qualitative_item_is_left_for_the_director_to_place(
        self, repo, created
    ):
        """Test an indicator with no dimension gets no aspect guessed for it."""

        await repo.create(
            self._payload(
                items=[{"description": "Trato", "target_type": "QUALITATIVE"}]
            )
        )

        assert created.add.call_args[0][0].items[0].aspect is None

    async def test_a_racing_duplicate_reads_like_the_ordinary_one(
        self, repo, created, mock_db
    ):
        """Test the unique constraint is turned into the domain error.

        Two requests can pass the service's check before either commits; the
        loser must get the same "ya existe" message as the ordinary case, not a
        500 from the driver.
        """

        mock_db.commit.side_effect = IntegrityError("stmt", {}, Exception("dup"))

        with pytest.raises(ValueError, match="Ya existe un plan"):
            await repo.create(self._payload())

        mock_db.rollback.assert_called_once()


class TestGetEvidence:
    """Reading one evidence row, scoped to its plan."""

    def test_is_scoped_to_the_plan(self, repo, mock_db):
        """Test an evidence of another plan is not returned."""

        mock_db.query.return_value.filter.return_value.first.return_value = None

        assert repo.get_evidence(1, 3) is None


class TestGetEvaluatedPeriods:
    """Only a period with grades already loaded can originate a plan."""

    async def test_maps_the_periods_it_finds(self, repo, mock_db):
        """Test each row becomes the option the creation page offers."""

        row = MagicMock(id=2, code="2025-1")
        row.name = "Primer semestre 2025"
        query = mock_db.query.return_value
        query.join.return_value = query
        query.filter.return_value = query
        query.distinct.return_value = query
        query.order_by.return_value = query
        query.all.return_value = [row]

        result = await repo.get_evaluated_periods(10)

        assert result == [
            {"id": 2, "code": "2025-1", "name": "Primer semestre 2025"}
        ]

    async def test_a_department_without_evaluations_offers_nothing(
        self, repo, mock_db
    ):
        """Test no grades means no period to originate a plan from."""

        query = mock_db.query.return_value
        query.join.return_value = query
        query.filter.return_value = query
        query.distinct.return_value = query
        query.order_by.return_value = query
        query.all.return_value = []

        assert await repo.get_evaluated_periods(10) == []


class TestBuildIndicators:
    """Every dimension and question flagged against the institutional threshold."""

    def test_covers_every_dimension_and_question_of_the_form(self, repo):
        """Test the director is offered the whole form, not only the low parts."""

        dimensions = repo._build_indicators({"001": 2.0}, 3.5)

        assert [d["dimension"] for d in dimensions] == list(DIMENSION_MAP)
        for entry in dimensions:
            assert [q["code"] for q in entry["questions"]] == DIMENSION_MAP[
                entry["dimension"]
            ]

    def test_a_score_on_the_threshold_counts_as_below(self, repo):
        """Test the threshold is inclusive.

        The institutional rule reads "igual o inferior"; a teacher sitting
        exactly on it is the case the plan exists for.
        """

        dimensions = repo._build_indicators({"001": 3.5}, 3.5)
        question = dimensions[0]["questions"][0]

        assert question["average"] == 3.5
        assert question["below_threshold"] is True

    def test_a_score_above_the_threshold_is_not_flagged(self, repo):
        dimensions = repo._build_indicators({"001": 3.6}, 3.5)

        assert dimensions[0]["questions"][0]["below_threshold"] is False

    def test_an_unscored_question_is_not_flagged(self, repo):
        """Test a question the teacher was never rated on raises nothing.

        ``None`` is "no data", and flagging it would put a compromiso in the
        acta about something nobody evaluated.
        """

        dimensions = repo._build_indicators({}, 3.5)

        for entry in dimensions:
            assert entry["average"] is None
            assert entry["below_threshold"] is False
            for question in entry["questions"]:
                assert question["below_threshold"] is False


class TestGetCandidates:
    """Who the creation page proposes a plan for, and why."""

    @pytest.fixture
    def stats(self, repo):
        """Stub everything the assembly reads, so the assembly itself is what
        is under test."""

        repo._teachers_with_plan = MagicMock(return_value=set())
        repo._high_risk_comment_counts = MagicMock(return_value={})
        repo.question_averages = MagicMock(return_value={})
        repo.get_department_context = MagicMock(
            return_value={"department_name": "Sistemas", "faculty_name": "Ingeniería"}
        )
        return repo

    def _ranking(self, *teachers):
        ranking = MagicMock()
        ranking.get_teacher_ranking_paginated = AsyncMock(
            return_value={"teachers": list(teachers)}
        )
        return patch(
            "api.repositories.improvement_plans.StatsRepository",
            return_value=ranking,
        )

    def _teacher(self, teacher_id=55, average=4.0):
        return {
            "teacher_id": teacher_id,
            "name": "Ada Lovelace",
            "avatar_url": None,
            "institutional_code": "1150",
            "overall_average": average,
        }

    async def test_returns_the_whole_department_by_default(self, stats):
        """Test the director sees everyone and decides.

        A teacher can average 4.0 and still be at 2.0 in one question, so the
        list is not pre-filtered unless asked.
        """

        with self._ranking(self._teacher(average=4.9)):
            result = await stats.get_candidates(10, 1, 3.5)

        assert [c["teacher_id"] for c in result] == [55]
        assert result[0]["below_threshold"] is False

    async def test_the_form_header_travels_with_every_candidate(self, stats):
        """Test the creation page proposes the header already filled in."""

        with self._ranking(self._teacher()):
            result = await stats.get_candidates(10, 1, 3.5)

        assert result[0]["department_name"] == "Sistemas"
        assert result[0]["faculty_name"] == "Ingeniería"

    async def test_an_average_on_the_threshold_is_below_it(self, stats):
        """Test the same inclusive rule the indicators use."""

        with self._ranking(self._teacher(average=3.5)):
            result = await stats.get_candidates(10, 1, 3.5)

        assert result[0]["below_threshold"] is True

    async def test_a_teacher_without_an_average_is_not_flagged(self, stats):
        """Test "not evaluated" is not the same as "evaluated badly"."""

        with self._ranking(self._teacher(average=None)):
            result = await stats.get_candidates(10, 1, 3.5)

        assert result[0]["below_threshold"] is False

    async def test_weak_questions_carry_the_dimension_they_belong_to(self, stats):
        """Test the director reads which part of the form a weak question is in."""

        stats.question_averages = MagicMock(return_value={55: {"017": 2.0}})

        with self._ranking(self._teacher()):
            result = await stats.get_candidates(10, 1, 3.5)

        weak = result[0]["weak_questions"]
        assert [q["target_ref"] for q in weak] == ["017"]
        assert weak[0]["dimension"] == "Procesos de Evaluación"

    async def test_at_risk_drops_a_teacher_who_already_has_a_plan(self, stats):
        """Test the auto-detection does not propose a plan twice."""

        stats._teachers_with_plan = MagicMock(return_value={55})

        with self._ranking(self._teacher(average=2.0)):
            result = await stats.get_candidates(10, 1, 3.5, only_at_risk=True)

        assert result == []

    async def test_at_risk_drops_a_teacher_nothing_is_wrong_with(self, stats):
        """Test a healthy teacher is not auto-detected."""

        with self._ranking(self._teacher(average=4.9)):
            result = await stats.get_candidates(10, 1, 3.5, only_at_risk=True)

        assert result == []

    async def test_at_risk_keeps_a_teacher_flagged_only_by_a_comment(self, stats):
        """Test a high-risk comment alone is enough to suggest a plan.

        The numbers can all be healthy while the students are writing something
        the director needs to act on.
        """

        stats._high_risk_comment_counts = MagicMock(return_value={55: 2})

        with self._ranking(self._teacher(average=4.9)):
            result = await stats.get_candidates(10, 1, 3.5, only_at_risk=True)

        assert [c["teacher_id"] for c in result] == [55]
        assert result[0]["high_risk_comment_count"] == 2

    async def test_at_risk_keeps_a_teacher_weak_in_a_single_question(self, stats):
        """Test one bad question is enough, even with a healthy average."""

        stats.question_averages = MagicMock(return_value={55: {"011": 2.0}})

        with self._ranking(self._teacher(average=4.9)):
            result = await stats.get_candidates(10, 1, 3.5, only_at_risk=True)

        assert [c["teacher_id"] for c in result] == [55]

    async def test_get_at_risk_is_the_narrowed_listing(self, repo):
        """Test the two endpoints cannot drift apart."""

        repo.get_candidates = AsyncMock(return_value=[])

        await repo.get_at_risk(10, 1, 3.5)

        repo.get_candidates.assert_awaited_once_with(
            department_id=10, period_id=1, threshold=3.5, only_at_risk=True
        )


class TestIndicatorLabel:
    """How a repeated indicator is named back to the director."""

    def test_the_overall_average_has_a_name_of_its_own(self, repo):
        assert repo._indicator_label("OVERALL_AVERAGE", None) == "Promedio general"

    def test_a_question_is_shown_with_its_text(self, repo):
        """Test a bare "017" would mean nothing to the reader."""

        label = repo._indicator_label("QUESTION", "017")

        assert label.startswith("017 — ")
        assert label != "017"

    def test_a_dimension_is_named_by_its_ref(self, repo):
        assert repo._indicator_label("DIMENSION", "Desempeño Docente") == (
            "Desempeño Docente"
        )

    def test_an_indicator_without_a_ref_falls_back_to_its_type(self, repo):
        """Test something always gets printed, never an empty cell."""

        assert repo._indicator_label("QUALITATIVE", None) == "QUALITATIVE"


class TestGetHistory:
    """What the teacher's record says across periods — and what repeats."""

    @pytest.fixture
    def history(self, repo, mock_db):
        """Stub the two queries and the stats side, leaving the assembly bare."""

        repo._period_question_averages = MagicMock(return_value={})
        repo._period_codes = MagicMock(return_value={})
        repo._teacher_info = MagicMock(return_value=("Ada Lovelace", None))
        repo._enrich_many = MagicMock(side_effect=lambda plans: [{"id": p.id} for p in plans])
        return repo

    _DEFAULT_TEACHER = object()

    def _wire(self, mock_db, *, teacher=_DEFAULT_TEACHER, plans=()):
        """Point the teacher lookup and the plan listing at fixed answers.

        ``teacher=None`` is the "no such teacher" case, so it needs a sentinel
        to be told apart from the default.
        """

        query = MagicMock()
        mock_db.query.return_value = query
        query.filter.return_value.first.return_value = (
            MagicMock(department_id=10)
            if teacher is self._DEFAULT_TEACHER
            else teacher
        )
        query.options.return_value.filter.return_value.order_by.return_value.all.return_value = list(
            plans
        )
        return query

    def _stats(self, *entries):
        stats = MagicMock()
        stats.get_teacher_history = AsyncMock(return_value=list(entries))
        return patch(
            "api.repositories.improvement_plans.StatsRepository", return_value=stats
        )

    def _item(self, target_type="QUESTION", target_ref="017"):
        return MagicMock(target_type=target_type, target_ref=target_ref)

    def _plan(self, plan_id, origin_period_id, items):
        return MagicMock(id=plan_id, origin_period_id=origin_period_id, items=items)

    async def test_an_unknown_teacher_answers_none(self, history, mock_db):
        """Test the route turns this into its 404."""

        self._wire(mock_db, teacher=None)

        assert await history.get_history(99) is None

    async def test_each_period_carries_its_dimension_averages(
        self, history, mock_db
    ):
        """Test the history is readable per dimension, not only overall.

        A teacher can hold a healthy overall average while one dimension keeps
        sinking, which is exactly what the record has to show.
        """

        self._wire(mock_db)
        history._period_question_averages = MagicMock(
            return_value={"2025-1": {"001": 2.0, "002": 4.0}}
        )

        with self._stats(
            {
                "period_code": "2025-1",
                "period_name": "Primer semestre",
                "overall_average": 3.2,
            }
        ):
            result = await history.get_history(55)

        period = result["periods"][0]
        assert period["period_code"] == "2025-1"
        assert period["overall_average"] == 3.2
        assert set(period["dimensions"]) == set(DIMENSION_MAP)
        assert period["dimensions"]["Desarrollo del Conocimiento"] == 3.0
        assert period["dimensions"]["Procesos de Evaluación"] is None

    async def test_the_same_indicator_in_two_periods_is_a_relapse(
        self, history, mock_db
    ):
        """Test an indicator committed to twice, in different periods, is flagged.

        That is the whole point of the record: a compromiso the teacher already
        signed once and is signing again.
        """

        plans = [
            self._plan(1, 1, [self._item()]),
            self._plan(2, 2, [self._item()]),
        ]
        self._wire(mock_db, plans=plans)
        history._period_codes = MagicMock(return_value={1: "2025-1", 2: "2025-2"})

        with self._stats():
            result = await history.get_history(55)

        assert len(result["recurrences"]) == 1
        recurrence = result["recurrences"][0]
        assert recurrence["target_ref"] == "017"
        assert recurrence["plan_ids"] == [1, 2]
        assert recurrence["period_codes"] == ["2025-1", "2025-2"]
        assert recurrence["label"].startswith("017 — ")

    async def test_two_plans_of_the_same_period_are_not_a_relapse(
        self, history, mock_db
    ):
        """Test relapsing means across periods, not twice in the same one.

        Two plans sharing an origin period describe one episode; calling that a
        relapse would accuse the teacher of repeating something they never got
        a semester to fix.
        """

        plans = [
            self._plan(1, 1, [self._item()]),
            self._plan(2, 1, [self._item()]),
        ]
        self._wire(mock_db, plans=plans)
        history._period_codes = MagicMock(return_value={1: "2025-1"})

        with self._stats():
            result = await history.get_history(55)

        assert result["recurrences"] == []

    async def test_a_single_plan_is_not_a_relapse(self, history, mock_db):
        """Test a first compromiso is just a compromiso."""

        self._wire(mock_db, plans=[self._plan(1, 1, [self._item()])])
        history._period_codes = MagicMock(return_value={1: "2025-1"})

        with self._stats():
            result = await history.get_history(55)

        assert result["recurrences"] == []

    async def test_qualitative_items_never_count_as_a_relapse(
        self, history, mock_db
    ):
        """Test a compromiso with no indicator cannot be compared across periods.

        They all share a null ``target_ref``, so grouping them would report a
        relapse between two unrelated commitments.
        """

        plans = [
            self._plan(1, 1, [self._item(target_type="QUALITATIVE", target_ref=None)]),
            self._plan(2, 2, [self._item(target_type="QUALITATIVE", target_ref=None)]),
        ]
        self._wire(mock_db, plans=plans)
        history._period_codes = MagicMock(return_value={1: "2025-1", 2: "2025-2"})

        with self._stats():
            result = await history.get_history(55)

        assert result["recurrences"] == []

    async def test_different_indicators_are_not_a_relapse(self, history, mock_db):
        """Test two plans about different things are two separate problems."""

        plans = [
            self._plan(1, 1, [self._item(target_ref="017")]),
            self._plan(2, 2, [self._item(target_ref="011")]),
        ]
        self._wire(mock_db, plans=plans)
        history._period_codes = MagicMock(return_value={1: "2025-1", 2: "2025-2"})

        with self._stats():
            result = await history.get_history(55)

        assert result["recurrences"] == []

    async def test_carries_the_teacher_header(self, history, mock_db):
        """Test the record identifies whose it is."""

        self._wire(mock_db)

        with self._stats():
            result = await history.get_history(55)

        assert result["teacher_id"] == 55
        assert result["teacher_name"] == "Ada Lovelace"
        assert result["department_id"] == 10
