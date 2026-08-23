"""
Tests for api.utils.plan_verification — the comparison that answers, a semester
late, whether an improvement plan actually worked.

Covers:
  - which period settles which plan, including the plans whose verification
    period was still unknown when they were drawn up
  - the verdict against the agreed target, and the per-subject breakdown that
    catches the same shortcoming moving to another course
  - the comment rule: ALTO raises the alert, MEDIO is context only
  - what the director is told, and that they are told once
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
    _indicator_label,
    _indicator_value,
    _notify_comments,
    _notify_scores,
    _previous_period_code,
    plans_to_verify,
    verify_plan_comments,
    verify_plan_scores,
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
