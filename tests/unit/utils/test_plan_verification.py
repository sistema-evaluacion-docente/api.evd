"""
Tests for api.utils.plan_verification — the comparison that answers, a semester
late, whether an improvement plan actually worked.

Covers:
  - which period settles which plan, including the plans whose verification
    period was still unknown when they were drawn up
  - the verdict against the agreed target, and the per-subject breakdown that
    catches the same shortcoming moving to another course
  - the comment rule: ALTO raises the alert, MEDIO is context only
  - what the director is told, that they are told once, and that it is the
    director currently running the department
  - the two entry points the evaluation processor hangs all of this off
"""

from unittest.mock import AsyncMock, MagicMock, patch

from api.models.academic_period import AcademicPeriodModel
from api.models.director import DirectorsModel
from api.models.improvement_plan import ImprovementPlanModel
from api.models.improvement_plan_verification_comment import (
    ImprovementPlanVerificationCommentModel,
)
from api.models.improvement_plan_verification_course import (
    ImprovementPlanVerificationCourseModel,
)
from api.models.improvement_plan_verification_item import (
    ImprovementPlanVerificationItemModel,
)
from api.models.notification import NotificationModel
from api.utils.plan_verification import (
    COMMENTS_ALERT_TITLE,
    COURSE_ALERT_TITLE,
    SCORES_ALERT_TITLE,
    _director_user_id,
    _indicator_label,
    _indicator_value,
    _notify_comments,
    _notify_scores,
    _previous_period_code,
    plans_to_verify,
    verify_comments_for_evaluation,
    verify_plan_comments,
    verify_plan_scores,
    verify_scores_for_evaluation,
)

MODULE = "api.utils.plan_verification"


class _FakeQuery:
    """Minimal stand-in for the chained SQLAlchemy query used in the module."""

    def __init__(self, first_result=None, all_result=None):
        self._first_result = first_result
        self._all_result = all_result if all_result is not None else []

    def options(self, *_a, **_k):
        return self

    def join(self, *_a, **_k):
        return self

    def outerjoin(self, *_a, **_k):
        return self

    def filter(self, *_a, **_k):
        return self

    def distinct(self):
        return self

    def group_by(self, *_a, **_k):
        return self

    def first(self):
        return self._first_result

    def all(self):
        return self._all_result


class _RecordingQuery(_FakeQuery):
    """`_FakeQuery` that keeps what it was filtered by, so a test can read it.

    The base fake drops its filters on the floor, which is fine while the thing
    under test is the result — but useless when the filter *is* the behaviour.
    """

    def __init__(self, first_result=None, all_result=None):
        super().__init__(first_result, all_result)
        self.filters: list = []

    def filter(self, *criteria, **_k):
        self.filters.extend(criteria)
        return self


def _make_db(queries: dict):
    db = MagicMock()
    db.query.side_effect = lambda *models: queries.get(
        models[0], _FakeQuery()
    )

    next_id = {"value": 0}

    def fake_flush():
        for call in db.add.call_args_list:
            obj = call.args[0]
            if getattr(obj, "id", None) is None:
                next_id["value"] += 1
                obj.id = next_id["value"]

    db.flush.side_effect = fake_flush

    return db


def _added(db, model):
    return [
        call.args[0] for call in db.add.call_args_list if isinstance(call.args[0], model)
    ]


def _item(item_id, target_type, target_ref=None, target_value=None):
    item = MagicMock()
    item.id = item_id
    item.target_type = target_type
    item.target_ref = target_ref
    item.target_value = target_value
    item.result_value = None
    item.status = "PENDIENTE"
    return item


def _plan(items, plan_id=7, teacher_id=3, title="Plan de prueba"):
    plan = MagicMock()
    plan.id = plan_id
    plan.teacher_id = teacher_id
    plan.title = title
    plan.department_id = 1
    plan.items = items
    return plan


def _verification(verification_id=10):
    verification = MagicMock()
    verification.id = verification_id
    verification.items = []
    verification.comment_findings = []
    verification.result = None
    verification.scores_verified_at = None
    verification.comments_verified_at = None
    verification.scores_notified_at = None
    verification.comments_notified_at = None
    return verification


class TestPreviousPeriodCode:
    """The inverse of the rule that picks a plan's verification period."""

    def test_second_semester_verifies_the_first_of_the_same_year(self):
        assert _previous_period_code("2025-2") == "2025-1"

    def test_first_semester_verifies_the_second_of_the_year_before(self):
        assert _previous_period_code("2026-1") == "2025-2"

    def test_unparseable_code_is_not_guessed(self):
        assert _previous_period_code("2025") is None
        assert _previous_period_code("dos mil-uno") is None


class TestIndicatorValue:
    """Reading one indicator out of a set of averages."""

    def test_question_is_read_by_its_code(self):
        assert _indicator_value("QUESTION", "011", None, {"011": 2.8}) == 2.8

    def test_dimension_averages_the_questions_it_has_data_for(self):
        # "Desempeño Docente" holds 007-014; only two were answered.
        value = _indicator_value(
            "DIMENSION", "Desempeño Docente", None, {"007": 4.0, "011": 3.0}
        )

        assert value == 3.5

    def test_dimension_without_any_of_its_questions_has_no_value(self):
        assert _indicator_value("DIMENSION", "Desempeño Docente", None, {"001": 5.0}) is None

    def test_overall_average_ignores_the_question_averages(self):
        assert _indicator_value("OVERALL_AVERAGE", None, 4.1, {"011": 1.0}) == 4.1

    def test_question_label_reads_the_question_not_its_code(self):
        assert _indicator_label("QUESTION", "011") == "«Asiste puntualmente a clase.»"


class TestPlansToVerify:
    """Which plans a freshly uploaded period settles."""

    def _period(self, period_id, code):
        period = MagicMock(spec=AcademicPeriodModel)
        period.id = period_id
        period.code = code
        return period

    def test_plan_left_without_a_verification_period_is_still_found(self):
        """The pointer is null on every plan drawn up before the following
        period existed in the catalogue — which is the normal case."""

        plan = MagicMock(spec=ImprovementPlanModel)
        plan.verification_period_id = None

        verification_period = self._period(2, "2025-2")
        origin_period = self._period(1, "2025-1")

        periods = _FakeQuery(first_result=verification_period)
        db = MagicMock()

        # First lookup resolves the uploaded period, second the origin it
        # would have come from; the plan query answers with the plan.
        results = [verification_period, origin_period]
        periods.first = lambda: results.pop(0) if results else None
        db.query.side_effect = lambda *models: (
            periods
            if models[0] is AcademicPeriodModel
            else _FakeQuery(all_result=[plan])
        )

        found = plans_to_verify(db, period_id=2)

        assert found == [plan]
        # And the pointer stops being a special case for the next run.
        assert plan.verification_period_id == 2

    def test_no_teachers_means_nothing_to_verify(self):
        db = MagicMock()
        db.query.side_effect = lambda *models: _FakeQuery(
            first_result=self._period(2, "2025-2")
        )

        assert plans_to_verify(db, period_id=2, teacher_ids=[]) == []


class TestVerifyPlanScores:
    """The verdict against what the acta agreed."""

    def _run(self, items, question_averages, overall=None, groups=(None, None)):
        plan = _plan(items)
        verification = _verification()
        db = _make_db({})

        repository = MagicMock()
        repository.question_averages.return_value = {plan.teacher_id: question_averages}

        group_averages, group_meta = groups

        with (
            patch(f"{MODULE}.ImprovementPlansRepository", return_value=repository),
            patch(f"{MODULE}._overall_average", return_value=overall),
            patch(
                f"{MODULE}._group_question_averages",
                return_value=(group_averages or {}, group_meta or {}),
            ),
            patch(f"{MODULE}._group_overall_averages", return_value={}),
            patch(f"{MODULE}._upsert_verification", return_value=verification),
        ):
            result = verify_plan_scores(db, plan, period_id=2, threshold=3.5)

        return result, db, plan

    def test_target_reached_reads_as_improved(self):
        items = [_item(1, "QUESTION", "011", 3.8)]

        verification, db, _ = self._run(items, {"011": 4.0})

        assert verification.result == "MEJORO"
        rows = _added(db, ImprovementPlanVerificationItemModel)
        assert len(rows) == 1
        assert rows[0].met is True
        assert float(rows[0].result_value) == 4.0

    def test_target_missed_reads_as_not_improved(self):
        items = [_item(1, "QUESTION", "011", 3.8)]

        verification, db, _ = self._run(items, {"011": 3.2})

        assert verification.result == "NO_MEJORO"
        assert _added(db, ImprovementPlanVerificationItemModel)[0].met is False

    def test_item_without_a_target_falls_back_to_the_institutional_threshold(self):
        items = [_item(1, "QUESTION", "011", None)]

        verification, db, _ = self._run(items, {"011": 3.4})

        row = _added(db, ImprovementPlanVerificationItemModel)[0]
        assert float(row.target_value) == 3.5
        assert row.met is False
        assert verification.result == "NO_MEJORO"

    def test_indicator_without_grades_is_not_counted_as_failed(self):
        """The teacher was never asked that question again: missing data is not
        a breach of what was agreed."""

        items = [_item(1, "QUESTION", "011", 3.8)]

        verification, db, _ = self._run(items, {})

        assert verification.result == "SIN_DATOS"
        assert _added(db, ImprovementPlanVerificationItemModel)[0].met is None

    def test_one_missed_target_among_several_is_enough(self):
        items = [_item(1, "QUESTION", "011", 3.5), _item(2, "QUESTION", "008", 3.5)]

        verification, _, _ = self._run(items, {"011": 4.2, "008": 2.9})

        assert verification.result == "NO_MEJORO"

    def test_breakdown_flags_the_subject_the_general_average_hides(self):
        """The case the whole breakdown exists for: cleared on the overall
        average, still under the target in one course."""

        items = [_item(1, "QUESTION", "011", 3.5)]
        group_averages = {41: {"011": 2.4}, 42: {"011": 4.6}}
        group_meta = {
            41: {"course_name": "POO I", "course_code": "1155", "group_name": "A"},
            42: {"course_name": "Estructuras", "course_code": "1160", "group_name": "B"},
        }

        verification, db, _ = self._run(
            items, {"011": 3.6}, groups=(group_averages, group_meta)
        )

        assert verification.result == "MEJORO"

        courses = _added(db, ImprovementPlanVerificationCourseModel)
        by_name = {row.course_name: row for row in courses}
        assert by_name["POO I"].met is False
        assert by_name["Estructuras"].met is True

    def test_the_signed_plan_items_are_left_untouched(self):
        """The Formato 3 was printed and signed with these values; the
        verification is a separate record, never a rewrite of the closing."""

        items = [_item(1, "QUESTION", "011", 3.8)]

        self._run(items, {"011": 2.0})

        assert items[0].result_value is None
        assert items[0].status == "PENDIENTE"

    def test_a_plan_with_nothing_measurable_is_skipped(self):
        verification, db, _ = self._run([_item(1, "QUALITATIVE")], {"011": 2.0})

        assert verification is None
        assert not _added(db, ImprovementPlanVerificationItemModel)


class TestVerifyPlanComments:
    """Reincidencia: the complaint behind a commitment coming back."""

    def _comment_row(self, comment_id, risk, category_id=9, category_name="Puntualidad"):
        row = MagicMock()
        row.comment_id = comment_id
        row.risk_level_name = risk
        row.category_id = category_id
        row.category_name = category_name
        return row

    def _run(self, items, cited_categories, comments):
        plan = _plan(items)
        verification = _verification()
        db = _make_db({})

        with (
            patch(f"{MODULE}._cited_categories", return_value=cited_categories),
            patch(f"{MODULE}._period_comments", return_value=comments),
            patch(f"{MODULE}._upsert_verification", return_value=verification),
        ):
            verify_plan_comments(db, plan, period_id=2)

        return db

    def test_high_risk_in_the_cited_category_raises_the_alert(self):
        db = self._run(
            [_item(1, "QUALITATIVE")],
            {1: {9}},
            [self._comment_row(100, "ALTO")],
        )

        findings = _added(db, ImprovementPlanVerificationCommentModel)
        assert len(findings) == 1
        assert findings[0].is_alert is True
        assert findings[0].category_name == "Puntualidad"

    def test_medium_risk_is_kept_as_context_without_alerting(self):
        db = self._run(
            [_item(1, "QUALITATIVE")],
            {1: {9}},
            [self._comment_row(101, "MEDIO")],
        )

        findings = _added(db, ImprovementPlanVerificationCommentModel)
        assert len(findings) == 1
        assert findings[0].is_alert is False

    def test_another_category_is_not_the_plan_coming_back(self):
        """A high-risk comment about something the plan never spoke about must
        not be read as the commitment failing."""

        db = self._run(
            [_item(1, "QUALITATIVE")],
            {1: {9}},
            [self._comment_row(102, "ALTO", category_id=4, category_name="Evaluación")],
        )

        assert not _added(db, ImprovementPlanVerificationCommentModel)

    def test_uncategorised_citation_falls_back_to_plain_high_risk(self):
        db = self._run(
            [_item(1, "QUALITATIVE")],
            {},
            [self._comment_row(103, "ALTO"), self._comment_row(104, "MEDIO")],
        )

        findings = _added(db, ImprovementPlanVerificationCommentModel)
        assert [f.comment_id for f in findings] == [103]
        assert findings[0].item_id is None


class TestNotifications:
    """What reaches the director's bell."""

    def _row(self, target_type, target_ref, target_value, result_value, met):
        row = MagicMock(spec=ImprovementPlanVerificationItemModel)
        row.target_type = target_type
        row.target_ref = target_ref
        row.target_value = target_value
        row.result_value = result_value
        row.met = met
        return row

    def _course_row(self, item_row, course_name, group_name, value):
        row = MagicMock(spec=ImprovementPlanVerificationCourseModel)
        row.course_name = course_name
        row.group_name = group_name
        row.result_value = value
        row.item = item_row
        return row

    def _db(self, item_rows, course_rows, director_user_id=55):
        director = MagicMock(spec=DirectorsModel)
        director.user_id = director_user_id

        return _make_db(
            {
                ImprovementPlanVerificationItemModel: _FakeQuery(all_result=item_rows),
                ImprovementPlanVerificationCourseModel: _FakeQuery(
                    all_result=course_rows
                ),
                DirectorsModel: _FakeQuery(first_result=director),
            }
        )

    def _notify(self, db, plan, verification, notify=_notify_scores):
        repository = MagicMock()
        repository.get_teacher_contact.return_value = {"name": "Ana Pérez"}

        with (
            patch(f"{MODULE}.ImprovementPlansRepository", return_value=repository),
            patch(f"{MODULE}.notification_manager") as manager,
        ):
            manager.broadcast = AsyncMock()
            notify(db, plan, verification, "2025-2", 1)

        return _added(db, NotificationModel)

    def test_missed_target_names_the_indicator_and_the_numbers(self):
        rows = [self._row("QUESTION", "011", 3.80, 2.90, False)]
        verification = _verification()
        db = self._db(rows, [])

        sent = self._notify(db, _plan([]), verification)

        assert len(sent) == 1
        assert sent[0].title == SCORES_ALERT_TITLE
        assert "Ana Pérez" in sent[0].message
        assert "Asiste puntualmente a clase" in sent[0].message
        assert "2.90" in sent[0].message and "3.80" in sent[0].message
        assert sent[0].link == "/planes/7"
        assert verification.scores_notified_at is not None

    def test_the_director_is_not_told_twice(self):
        verification = _verification()
        verification.scores_notified_at = "ya"
        db = self._db([self._row("QUESTION", "011", 3.8, 2.9, False)], [])

        assert self._notify(db, _plan([]), verification) == []

    def test_clearing_the_target_in_general_still_reports_the_weak_subject(self):
        item_row = self._row("QUESTION", "011", 3.50, 3.60, True)
        course = self._course_row(item_row, "POO I", "A", 2.40)
        verification = _verification()
        db = self._db([item_row], [course])

        sent = self._notify(db, _plan([]), verification)

        assert len(sent) == 1
        assert sent[0].title == COURSE_ALERT_TITLE
        assert "POO I" in sent[0].message

    def test_nothing_is_sent_when_every_subject_cleared_the_target(self):
        item_row = self._row("QUESTION", "011", 3.5, 4.2, True)
        verification = _verification()
        db = self._db([item_row], [])

        assert self._notify(db, _plan([]), verification) == []
        assert verification.scores_notified_at is None

    def test_nothing_is_sent_when_the_period_had_no_grades_for_the_indicator(self):
        verification = _verification()
        db = self._db([self._row("QUESTION", "011", 3.5, None, None)], [])

        assert self._notify(db, _plan([]), verification) == []

    def test_comment_reincidence_names_the_category(self):
        finding = MagicMock(spec=ImprovementPlanVerificationCommentModel)
        finding.category_name = "Puntualidad"
        verification = _verification()
        db = self._db([], [])
        db.query.side_effect = lambda *models: (
            _FakeQuery(all_result=[finding])
            if models[0] is ImprovementPlanVerificationCommentModel
            else _FakeQuery(first_result=self._director())
        )

        sent = self._notify(db, _plan([]), verification, notify=_notify_comments)

        assert len(sent) == 1
        assert sent[0].title == COMMENTS_ALERT_TITLE
        assert "Puntualidad" in sent[0].message
        assert verification.comments_notified_at is not None

    def _director(self):
        director = MagicMock(spec=DirectorsModel)
        director.user_id = 55
        return director


class TestDirectorLookup:
    """Who the alert is addressed to."""

    def _db(self, directors):
        return _make_db({DirectorsModel: _FakeQuery(first_result=directors)})

    def _director(self, user_id):
        director = MagicMock(spec=DirectorsModel)
        director.user_id = user_id
        return director

    def test_reads_the_department_the_plan_carries(self):
        plan = _plan([])
        plan.department_id = 4

        assert _director_user_id(self._db(self._director(55)), plan, 9) == 55

    def test_falls_back_to_the_department_of_the_evaluation(self):
        # `improvement_plans.department_id` is nullable, and a plan drawn up
        # before the column existed has none.
        plan = _plan([])
        plan.department_id = None

        assert _director_user_id(self._db(self._director(55)), plan, 9) == 55

    def test_with_no_department_at_all_there_is_nobody_to_tell(self):
        plan = _plan([])
        plan.department_id = None

        assert _director_user_id(self._db(self._director(55)), plan, None) is None

    def test_a_department_without_an_active_director_is_left_alone(self):
        plan = _plan([])
        plan.department_id = 4

        assert _director_user_id(self._db(None), plan, 9) is None

    def test_asks_for_the_director_currently_running_the_department(self):
        # A department keeps the rows of whoever ran it before, so filtering by
        # department alone hands back whichever one the database returns first —
        # often a former director, while the current one hears nothing. The
        # fake query ignores its filters, so the criteria are read back instead.
        plan = _plan([])
        plan.department_id = 4
        query = _RecordingQuery()

        _director_user_id(_make_db({DirectorsModel: query}), plan, 9)

        criteria = [str(criterion) for criterion in query.filters]
        assert any("department_id" in criterion for criterion in criteria)
        assert any("active" in criterion for criterion in criteria)


def _evaluation(evaluation_id=12, period_id=3, period_code="2025-2", department_id=1):
    evaluation = MagicMock()
    evaluation.id = evaluation_id
    evaluation.academic_period_id = period_id
    evaluation.department_id = department_id

    if period_code is None:
        evaluation.academic_period = None
    else:
        period = MagicMock(spec=AcademicPeriodModel)
        period.code = period_code
        evaluation.academic_period = period

    return evaluation


class TestVerifyScoresForEvaluation:
    """The hook the evaluation processor calls once the grades have landed.

    Hangs off the processing and not off the AI analysis, which is triggered by
    hand: a director who never runs the analysis must still get the numbers
    verified.
    """

    def _run(self, evaluation, *, plans, verification=None, threshold=3.5):
        db = MagicMock()

        with (
            patch(f"{MODULE}.evaluated_teacher_ids", return_value=[3]) as teachers,
            patch(f"{MODULE}.plans_to_verify", return_value=plans) as to_verify,
            patch(f"{MODULE}.score_threshold", return_value=threshold),
            patch(
                f"{MODULE}.verify_plan_scores", return_value=verification
            ) as verify,
            patch(f"{MODULE}._notify_scores") as notify,
        ):
            verify_scores_for_evaluation(db, evaluation)

        return db, teachers, to_verify, verify, notify

    def test_verifies_and_reports_every_plan_this_evaluation_settles(self):
        plans = [_plan([], plan_id=7), _plan([], plan_id=8)]
        _, _, _, verify, notify = self._run(
            _evaluation(), plans=plans, verification=_verification()
        )

        assert verify.call_count == 2
        assert notify.call_count == 2
        # The period code the alert says it happened in comes off the evaluation.
        assert notify.call_args[0][3] == "2025-2"
        assert notify.call_args[0][4] == 1

    def test_narrows_to_the_teachers_this_evaluation_brought_grades_for(self):
        _, teachers, to_verify, _, _ = self._run(
            _evaluation(), plans=[_plan([])], verification=_verification()
        )

        teachers.assert_called_once()
        assert to_verify.call_args[0][1:] == (3, [3])

    def test_a_plan_with_nothing_to_compare_is_not_reported(self):
        _, _, _, _, notify = self._run(
            _evaluation(), plans=[_plan([])], verification=None
        )

        notify.assert_not_called()

    def test_an_evaluation_without_a_period_settles_nothing(self):
        evaluation = _evaluation()
        evaluation.academic_period_id = None

        _, _, to_verify, _, notify = self._run(evaluation, plans=[_plan([])])

        to_verify.assert_not_called()
        notify.assert_not_called()

    def test_says_nothing_about_where_when_the_period_has_no_code(self):
        _, _, _, _, notify = self._run(
            _evaluation(period_code=None),
            plans=[_plan([])],
            verification=_verification(),
        )

        assert notify.call_args[0][3] is None

    def test_a_failure_here_never_undoes_an_upload_that_worked(self):
        # Best-effort by design: the grades are already stored by the time this
        # runs, and a verification that blows up must not fail the upload.
        db = MagicMock()

        with (
            patch(f"{MODULE}.evaluated_teacher_ids", return_value=[3]),
            patch(f"{MODULE}.plans_to_verify", side_effect=RuntimeError("boom")),
            patch(f"{MODULE}.logger") as logger,
        ):
            verify_scores_for_evaluation(db, _evaluation())

        logger.warning.assert_called_once()


class TestVerifyCommentsForEvaluation:
    """The hook that looks for the complaint behind a commitment coming back.

    Only once the analysis has run: a comment carries no risk level nor
    pedagogical category until the AI has classified it.
    """

    def _run(self, evaluation, *, plans, verification=None):
        db = MagicMock()

        with (
            patch(f"{MODULE}.evaluated_teacher_ids", return_value=[3]),
            patch(f"{MODULE}.plans_to_verify", return_value=plans),
            patch(
                f"{MODULE}.verify_plan_comments", return_value=verification
            ) as verify,
            patch(f"{MODULE}._notify_comments") as notify,
        ):
            verify_comments_for_evaluation(db, evaluation)

        return verify, notify

    def test_reports_the_reincidencia_of_every_plan_of_the_period(self):
        plans = [_plan([], plan_id=7), _plan([], plan_id=8)]
        verify, notify = self._run(
            _evaluation(), plans=plans, verification=_verification()
        )

        assert verify.call_count == 2
        assert notify.call_count == 2

    def test_a_plan_whose_complaints_did_not_come_back_is_not_reported(self):
        _, notify = self._run(_evaluation(), plans=[_plan([])], verification=None)

        notify.assert_not_called()

    def test_an_evaluation_without_a_period_settles_nothing(self):
        evaluation = _evaluation()
        evaluation.academic_period_id = None

        verify, notify = self._run(evaluation, plans=[_plan([])])

        verify.assert_not_called()
        notify.assert_not_called()

    def test_a_failure_here_never_undoes_an_analysis_that_worked(self):
        db = MagicMock()

        with (
            patch(f"{MODULE}.evaluated_teacher_ids", return_value=[3]),
            patch(f"{MODULE}.plans_to_verify", side_effect=RuntimeError("boom")),
            patch(f"{MODULE}.logger") as logger,
        ):
            verify_comments_for_evaluation(db, _evaluation())

        logger.warning.assert_called_once()
