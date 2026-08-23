"""
Tests for the high-risk comment notification logic in
api.utils.evaluation_processor.

Covers:
  - _create_high_risk_comment_notification: the low-level helper that
    creates and broadcasts the alert notification.
  - analyze_evaluation_comments: the background task that classifies
    comments and must trigger that helper when a comment is classified
    with risk_level == HIGH_RISK_LEVEL_ID (ALTO).
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from api.models.comment import CommentModel
from api.models.comment_pedagogical_category import CommentPedagogicalCategoryModel
from api.models.director import DirectorsModel
from api.models.evaluation import EvaluationModel
from api.models.notification import NotificationModel
from api.models.pedagogical_category import PedagogicalCategoryModel
from api.models.risk_level import RiskLevelModel
from api.models.teacher import TeacherModel
from api.utils.evaluation_processor import (
    HIGH_RISK_LEVEL_ID,
    PLAN_SUGGESTION_TITLE,
    _contract_type_name,
    _create_high_risk_comment_notification,
    _create_plan_suggestion_notification,
    analyze_evaluation_comments,
)


def _risk_level(level_id: int, name: str) -> MagicMock:
    risk_level = MagicMock()
    risk_level.id = level_id
    risk_level.name = name
    return risk_level


def _category(category_id: int, name: str) -> MagicMock:
    category = MagicMock()
    category.id = category_id
    category.name = name
    return category


class _FakeQuery:
    """Minimal stand-in for the chained SQLAlchemy query used in the module.

    Configured per model with the value(s) `.first()`/`.all()` should return.
    """

    def __init__(self, first_result=None, all_result=None, first_results=None):
        self._first_result = first_result
        self._all_result = all_result if all_result is not None else []
        self._first_results = list(first_results) if first_results else None

    def filter(self, *_args, **_kwargs):
        return self

    def first(self):
        if self._first_results is not None:
            return self._first_results.pop(0) if self._first_results else None
        return self._first_result

    def all(self):
        return self._all_result


def _make_db(
    evaluation,
    comments,
    risk_levels,
    categories,
    director,
    teacher_first_results=None,
):
    """Build a MagicMock db whose .query(Model) dispatches to a _FakeQuery."""

    queries = {
        EvaluationModel: _FakeQuery(first_result=evaluation),
        CommentModel: _FakeQuery(all_result=comments),
        RiskLevelModel: _FakeQuery(all_result=risk_levels),
        PedagogicalCategoryModel: _FakeQuery(all_result=categories),
        DirectorsModel: _FakeQuery(first_result=director),
        TeacherModel: _FakeQuery(first_results=teacher_first_results),
    }

    db = MagicMock()
    db.query.side_effect = lambda model: queries[model]

    # Simulate the DB assigning autoincrement ids to newly added
    # notifications on flush, so NotificationEvent(notification_id=...)
    # can be built (it requires an int).
    next_id = {"value": 0}

    def fake_flush():
        for call in db.add.call_args_list:
            obj = call.args[0]
            if isinstance(obj, NotificationModel) and obj.id is None:
                next_id["value"] += 1
                obj.id = next_id["value"]

    db.flush.side_effect = fake_flush

    return db


def _added_notifications(db, title: str) -> list[NotificationModel]:
    return [
        call.args[0]
        for call in db.add.call_args_list
        if isinstance(call.args[0], NotificationModel) and call.args[0].title == title
    ]


class TestAnalyzeEvaluationCommentsHighRiskNotification:
    """Tests for the risk-level-3 (ALTO) alert wired into analyze_evaluation_comments."""

    def _make_evaluation(self, department_id=1, academic_period_name="2024-1"):
        evaluation = MagicMock(spec=EvaluationModel)
        evaluation.id = 1
        evaluation.department_id = department_id
        evaluation.user_id = 99
        evaluation.academic_period = MagicMock()
        evaluation.academic_period.name = academic_period_name
        return evaluation

    def _make_comment(self, comment_id, teacher_id, text="Comentario de prueba"):
        comment = MagicMock(spec=CommentModel)
        comment.id = comment_id
        comment.teacher_id = teacher_id
        comment.original_text = text
        comment.risk_level = None
        comment.risk_score = None
        return comment

    def _make_director(self, user_id=55):
        director = MagicMock(spec=DirectorsModel)
        director.user_id = user_id
        return director

    def _make_teacher(self, teacher_id, name):
        teacher = MagicMock(spec=TeacherModel)
        teacher.id = teacher_id
        teacher.user = MagicMock()
        teacher.user.name = name
        return teacher

    @patch("api.utils.evaluation_processor.notification_manager")
    @patch("api.utils.evaluation_processor.analyze_comment")
    @patch("api.utils.evaluation_processor.SessionLocal")
    def test_notifies_director_when_comment_is_high_risk(
        self, mock_session_local, mock_analyze_comment, mock_notification_manager
    ):
        evaluation = self._make_evaluation(department_id=1)
        comment = self._make_comment(comment_id=10, teacher_id=7)
        director = self._make_director(user_id=55)
        teacher = self._make_teacher(teacher_id=7, name="Juan Perez")

        db = _make_db(
            evaluation=evaluation,
            comments=[comment],
            risk_levels=[
                _risk_level(1, "BAJO"),
                _risk_level(2, "MEDIO"),
                _risk_level(3, "ALTO"),
            ],
            categories=[],
            director=director,
            teacher_first_results=[teacher],
        )
        mock_session_local.return_value = db
        mock_analyze_comment.return_value = {
            "risk_label": "ALTO",
            "risk_score": 0.95,
            "category_labels": [],
        }
        mock_notification_manager.broadcast = AsyncMock()

        analyze_evaluation_comments(evaluation.id)

        assert comment.risk_level == HIGH_RISK_LEVEL_ID

        alerts = _added_notifications(db, "Alerta: comentario de riesgo alto")
        assert len(alerts) == 1
        assert alerts[0].user_id == 55
        assert alerts[0].type == "warning"
        assert "Juan Perez" in alerts[0].message
        assert str(evaluation.id) in alerts[0].message
        assert alerts[0].link == "/docentes/7?period=2024-1"

        channels_notified = {
            call.args[0] for call in mock_notification_manager.broadcast.call_args_list
        }
        assert "notifications:55" in channels_notified

    @patch("api.utils.evaluation_processor.notification_manager")
    @patch("api.utils.evaluation_processor.analyze_comment")
    @patch("api.utils.evaluation_processor.SessionLocal")
    def test_does_not_notify_for_low_or_medium_risk(
        self, mock_session_local, mock_analyze_comment, mock_notification_manager
    ):
        evaluation = self._make_evaluation(department_id=1)
        comment = self._make_comment(comment_id=11, teacher_id=7)
        director = self._make_director(user_id=55)

        db = _make_db(
            evaluation=evaluation,
            comments=[comment],
            risk_levels=[
                _risk_level(1, "BAJO"),
                _risk_level(2, "MEDIO"),
                _risk_level(3, "ALTO"),
            ],
            categories=[],
            director=director,
        )
        mock_session_local.return_value = db
        mock_analyze_comment.return_value = {
            "risk_label": "BAJO",
            "risk_score": 0.1,
            "category_labels": [],
        }
        mock_notification_manager.broadcast = AsyncMock()

        analyze_evaluation_comments(evaluation.id)

        assert comment.risk_level == 1
        assert _added_notifications(db, "Alerta: comentario de riesgo alto") == []

    @patch("api.utils.evaluation_processor.notification_manager")
    @patch("api.utils.evaluation_processor.analyze_comment")
    @patch("api.utils.evaluation_processor.SessionLocal")
    def test_skips_notification_when_department_has_no_director(
        self, mock_session_local, mock_analyze_comment, mock_notification_manager
    ):
        evaluation = self._make_evaluation(department_id=1)
        comment = self._make_comment(comment_id=12, teacher_id=7)

        db = _make_db(
            evaluation=evaluation,
            comments=[comment],
            risk_levels=[
                _risk_level(1, "BAJO"),
                _risk_level(2, "MEDIO"),
                _risk_level(3, "ALTO"),
            ],
            categories=[],
            director=None,
        )
        mock_session_local.return_value = db
        mock_analyze_comment.return_value = {
            "risk_label": "ALTO",
            "risk_score": 0.95,
            "category_labels": [],
        }
        mock_notification_manager.broadcast = AsyncMock()

        analyze_evaluation_comments(evaluation.id)

        assert comment.risk_level == HIGH_RISK_LEVEL_ID
        assert _added_notifications(db, "Alerta: comentario de riesgo alto") == []
        db.query.assert_any_call(DirectorsModel)
        assert TeacherModel not in [
            call.args[0]
            for call in db.query.call_args_list
            if call.args[0] is TeacherModel
        ]

    @patch("api.utils.evaluation_processor.notification_manager")
    @patch("api.utils.evaluation_processor.analyze_comment")
    @patch("api.utils.evaluation_processor.SessionLocal")
    def test_caches_teacher_lookup_across_multiple_high_risk_comments(
        self, mock_session_local, mock_analyze_comment, mock_notification_manager
    ):
        evaluation = self._make_evaluation(department_id=1)
        comment_a = self._make_comment(comment_id=20, teacher_id=7, text="Primero")
        comment_b = self._make_comment(comment_id=21, teacher_id=7, text="Segundo")
        director = self._make_director(user_id=55)
        teacher = self._make_teacher(teacher_id=7, name="Juan Perez")

        db = _make_db(
            evaluation=evaluation,
            comments=[comment_a, comment_b],
            risk_levels=[
                _risk_level(1, "BAJO"),
                _risk_level(2, "MEDIO"),
                _risk_level(3, "ALTO"),
            ],
            categories=[],
            director=director,
            # Only one TeacherModel lookup is expected: the second
            # high-risk comment for the same teacher should hit the cache.
            teacher_first_results=[teacher],
        )
        mock_session_local.return_value = db
        mock_analyze_comment.return_value = {
            "risk_label": "ALTO",
            "risk_score": 0.9,
            "category_labels": [],
        }
        mock_notification_manager.broadcast = AsyncMock()

        analyze_evaluation_comments(evaluation.id)

        teacher_query_calls = [
            call for call in db.query.call_args_list if call.args[0] is TeacherModel
        ]
        assert len(teacher_query_calls) == 1
        assert len(_added_notifications(db, "Alerta: comentario de riesgo alto")) == 2


class TestAnalyzeEvaluationCommentsPedagogicalCategories:
    """Tests for the 0..N pedagogical category assignment in analyze_evaluation_comments."""

    def _make_evaluation(self, department_id=1):
        evaluation = MagicMock(spec=EvaluationModel)
        evaluation.id = 1
        evaluation.department_id = department_id
        evaluation.user_id = 99
        return evaluation

    def _make_comment(
        self, comment_id, teacher_id=7, text="Comentario de prueba", categories=None
    ):
        comment = MagicMock(spec=CommentModel)
        comment.id = comment_id
        comment.teacher_id = teacher_id
        comment.original_text = text
        comment.risk_level = None
        comment.risk_score = None
        comment.pedagogical_category_ai_model = None
        comment.pedagogical_categories = categories if categories is not None else []
        return comment

    @patch("api.utils.evaluation_processor.notification_manager")
    @patch("api.utils.evaluation_processor.analyze_comment")
    @patch("api.utils.evaluation_processor.SessionLocal")
    def test_creates_one_row_per_category_above_threshold(
        self, mock_session_local, mock_analyze_comment, mock_notification_manager
    ):
        evaluation = self._make_evaluation()
        comment = self._make_comment(comment_id=30)

        db = _make_db(
            evaluation=evaluation,
            comments=[comment],
            risk_levels=[_risk_level(1, "BAJO")],
            categories=[
                _category(1, "CLARIDAD"),
                _category(2, "PUNTUALIDAD"),
            ],
            director=None,
        )
        mock_session_local.return_value = db
        mock_analyze_comment.return_value = {
            "risk_label": "BAJO",
            "risk_score": 0.1,
            "category_labels": [
                {"label": "CLARIDAD", "score": 0.9},
                {"label": "PUNTUALIDAD", "score": 0.6},
            ],
            "category_model": "org/category-model-v1",
        }
        mock_notification_manager.broadcast = AsyncMock()

        analyze_evaluation_comments(evaluation.id)

        links = comment.pedagogical_categories
        assert len(links) == 2
        assert {link.pedagogical_category_id for link in links} == {1, 2}
        assert {link.score for link in links} == {0.9, 0.6}
        assert all(isinstance(link, CommentPedagogicalCategoryModel) for link in links)

    @patch("api.utils.evaluation_processor.notification_manager")
    @patch("api.utils.evaluation_processor.analyze_comment")
    @patch("api.utils.evaluation_processor.SessionLocal")
    def test_no_labels_creates_no_category_rows(
        self, mock_session_local, mock_analyze_comment, mock_notification_manager
    ):
        evaluation = self._make_evaluation()
        comment = self._make_comment(comment_id=31)

        db = _make_db(
            evaluation=evaluation,
            comments=[comment],
            risk_levels=[_risk_level(1, "BAJO")],
            categories=[_category(1, "CLARIDAD")],
            director=None,
        )
        mock_session_local.return_value = db
        mock_analyze_comment.return_value = {
            "risk_label": "BAJO",
            "risk_score": 0.1,
            "category_labels": [],
            "category_model": "org/category-model-v1",
        }
        mock_notification_manager.broadcast = AsyncMock()

        analyze_evaluation_comments(evaluation.id)

        assert comment.pedagogical_categories == []

    @patch("api.utils.evaluation_processor.notification_manager")
    @patch("api.utils.evaluation_processor.analyze_comment")
    @patch("api.utils.evaluation_processor.SessionLocal")
    def test_re_analysis_replaces_the_categories_of_the_previous_run(
        self, mock_session_local, mock_analyze_comment, mock_notification_manager
    ):
        """Analysing twice must not leave the comment with duplicated categories."""

        evaluation = self._make_evaluation()
        comment = self._make_comment(
            comment_id=32,
            categories=[
                CommentPedagogicalCategoryModel(
                    comment_id=32, pedagogical_category_id=1, score=0.8
                )
            ],
        )

        db = _make_db(
            evaluation=evaluation,
            comments=[comment],
            risk_levels=[_risk_level(1, "BAJO")],
            categories=[_category(1, "CLARIDAD"), _category(2, "PUNTUALIDAD")],
            director=None,
        )
        mock_session_local.return_value = db
        mock_analyze_comment.return_value = {
            "risk_label": "BAJO",
            "risk_score": 0.1,
            "category_labels": [
                {"label": "CLARIDAD", "score": 0.9},
                {"label": "PUNTUALIDAD", "score": 0.6},
            ],
            "category_model": "org/category-model-v1",
        }
        mock_notification_manager.broadcast = AsyncMock()

        analyze_evaluation_comments(evaluation.id)

        links = comment.pedagogical_categories
        assert [link.pedagogical_category_id for link in links] == [1, 2]
        assert [link.score for link in links] == [0.9, 0.6]

    @patch("api.utils.evaluation_processor.notification_manager")
    @patch("api.utils.evaluation_processor.analyze_comment")
    @patch("api.utils.evaluation_processor.SessionLocal")
    def test_keeps_the_previous_categories_when_the_model_did_not_run(
        self, mock_session_local, mock_analyze_comment, mock_notification_manager
    ):
        """A model that is unconfigured or fails must not wipe a classification."""

        evaluation = self._make_evaluation()
        existing = CommentPedagogicalCategoryModel(
            comment_id=33, pedagogical_category_id=1, score=0.8
        )
        comment = self._make_comment(comment_id=33, categories=[existing])

        db = _make_db(
            evaluation=evaluation,
            comments=[comment],
            risk_levels=[_risk_level(1, "BAJO")],
            categories=[_category(1, "CLARIDAD")],
            director=None,
        )
        mock_session_local.return_value = db
        mock_analyze_comment.return_value = {
            "risk_label": "BAJO",
            "risk_score": 0.1,
            "category_labels": [],
            "category_model": None,
        }
        mock_notification_manager.broadcast = AsyncMock()

        analyze_evaluation_comments(evaluation.id)

        assert comment.pedagogical_categories == [existing]


class TestAnalyzeEvaluationCommentsModelAttribution:
    """Tests for persisting which AI model produced each classification."""

    def _make_evaluation(self, department_id=1):
        evaluation = MagicMock(spec=EvaluationModel)
        evaluation.id = 1
        evaluation.department_id = department_id
        evaluation.user_id = 99
        return evaluation

    def _make_comment(self, comment_id, teacher_id=7, text="Comentario de prueba"):
        comment = MagicMock(spec=CommentModel)
        comment.id = comment_id
        comment.teacher_id = teacher_id
        comment.original_text = text
        comment.risk_level = None
        comment.risk_score = None
        comment.risk_level_ai_model = None
        comment.pedagogical_category_ai_model = None
        return comment

    @patch("api.utils.evaluation_processor.notification_manager")
    @patch("api.utils.evaluation_processor.analyze_comment")
    @patch("api.utils.evaluation_processor.SessionLocal")
    def test_stores_both_model_ids_when_both_models_classified(
        self, mock_session_local, mock_analyze_comment, mock_notification_manager
    ):
        evaluation = self._make_evaluation()
        comment = self._make_comment(comment_id=40)

        db = _make_db(
            evaluation=evaluation,
            comments=[comment],
            risk_levels=[_risk_level(1, "BAJO")],
            categories=[_category(1, "CLARIDAD")],
            director=None,
        )
        mock_session_local.return_value = db
        mock_analyze_comment.return_value = {
            "risk_label": "BAJO",
            "risk_score": 0.1,
            "risk_model": "org/risk-model-v1",
            "category_labels": [{"label": "CLARIDAD", "score": 0.9}],
            "category_model": "org/category-model-v1",
        }
        mock_notification_manager.broadcast = AsyncMock()

        analyze_evaluation_comments(evaluation.id)

        assert comment.risk_level_ai_model == "org/risk-model-v1"
        assert comment.pedagogical_category_ai_model == "org/category-model-v1"

    @patch("api.utils.evaluation_processor.notification_manager")
    @patch("api.utils.evaluation_processor.analyze_comment")
    @patch("api.utils.evaluation_processor.SessionLocal")
    def test_leaves_risk_model_unset_when_risk_model_produced_no_label(
        self, mock_session_local, mock_analyze_comment, mock_notification_manager
    ):
        evaluation = self._make_evaluation()
        comment = self._make_comment(comment_id=41)

        db = _make_db(
            evaluation=evaluation,
            comments=[comment],
            risk_levels=[_risk_level(1, "BAJO")],
            categories=[_category(1, "CLARIDAD")],
            director=None,
        )
        mock_session_local.return_value = db
        mock_analyze_comment.return_value = {
            "risk_label": None,
            "risk_score": None,
            "risk_model": None,
            "category_labels": [{"label": "CLARIDAD", "score": 0.9}],
            "category_model": "org/category-model-v1",
        }
        mock_notification_manager.broadcast = AsyncMock()

        analyze_evaluation_comments(evaluation.id)

        assert comment.risk_level_ai_model is None
        assert comment.pedagogical_category_ai_model == "org/category-model-v1"

    @patch("api.utils.evaluation_processor.notification_manager")
    @patch("api.utils.evaluation_processor.analyze_comment")
    @patch("api.utils.evaluation_processor.SessionLocal")
    def test_leaves_category_model_unset_when_no_category_cleared_threshold(
        self, mock_session_local, mock_analyze_comment, mock_notification_manager
    ):
        """A comment with no assigned category has no category model to credit."""

        evaluation = self._make_evaluation()
        comment = self._make_comment(comment_id=42)

        db = _make_db(
            evaluation=evaluation,
            comments=[comment],
            risk_levels=[_risk_level(1, "BAJO")],
            categories=[_category(1, "CLARIDAD")],
            director=None,
        )
        mock_session_local.return_value = db
        mock_analyze_comment.return_value = {
            "risk_label": "BAJO",
            "risk_score": 0.1,
            "risk_model": "org/risk-model-v1",
            "category_labels": [],
            "category_model": "org/category-model-v1",
        }
        mock_notification_manager.broadcast = AsyncMock()

        analyze_evaluation_comments(evaluation.id)

        assert comment.risk_level_ai_model == "org/risk-model-v1"
        assert comment.pedagogical_category_ai_model is None


class TestCreateHighRiskCommentNotification:
    """Direct tests for the _create_high_risk_comment_notification helper."""

    def _make_db(self):
        db = MagicMock()
        next_id = {"value": 0}

        def fake_flush():
            for call in db.add.call_args_list:
                obj = call.args[0]
                if isinstance(obj, NotificationModel) and obj.id is None:
                    next_id["value"] += 1
                    obj.id = next_id["value"]

        db.flush.side_effect = fake_flush
        return db

    def _make_comment(self, comment_id=1, text="Comentario", teacher_id=7):
        comment = MagicMock(spec=CommentModel)
        comment.id = comment_id
        comment.original_text = text
        comment.teacher_id = teacher_id
        return comment

    @patch("api.utils.evaluation_processor.notification_manager")
    def test_creates_notification_and_broadcasts(self, mock_notification_manager):
        mock_notification_manager.broadcast = AsyncMock()
        db = self._make_db()
        comment = self._make_comment(comment_id=1, text="Este docente no explica nada")

        _create_high_risk_comment_notification(
            db,
            director_user_id=55,
            evaluation_id=3,
            teacher_name="Ana Gomez",
            comment=comment,
        )

        db.add.assert_called_once()
        notification = db.add.call_args.args[0]
        assert isinstance(notification, NotificationModel)
        assert notification.user_id == 55
        assert notification.title == "Alerta: comentario de riesgo alto"
        assert notification.type == "warning"
        assert "Ana Gomez" in notification.message
        assert "Este docente no explica nada" in notification.message
        assert notification.link == "/docentes/7"

        db.flush.assert_called_once()
        mock_notification_manager.broadcast.assert_called_once()
        channel, event = mock_notification_manager.broadcast.call_args.args
        assert channel == "notifications:55"
        assert event.user_id == 55
        assert event.notification_type == "warning"
        assert event.link == "/docentes/7"

    @patch("api.utils.evaluation_processor.notification_manager")
    def test_link_includes_period_when_provided(self, mock_notification_manager):
        mock_notification_manager.broadcast = AsyncMock()
        db = self._make_db()
        comment = self._make_comment(comment_id=4, teacher_id=9)

        _create_high_risk_comment_notification(
            db,
            director_user_id=55,
            evaluation_id=3,
            teacher_name="Ana Gomez",
            comment=comment,
            academic_period_name="2024-1",
        )

        notification = db.add.call_args.args[0]
        assert notification.link == "/docentes/9?period=2024-1"

    @patch("api.utils.evaluation_processor.notification_manager")
    def test_link_url_encodes_period_name(self, mock_notification_manager):
        mock_notification_manager.broadcast = AsyncMock()
        db = self._make_db()
        comment = self._make_comment(comment_id=5, teacher_id=9)

        _create_high_risk_comment_notification(
            db,
            director_user_id=55,
            evaluation_id=3,
            teacher_name="Ana Gomez",
            comment=comment,
            academic_period_name="2024 Primer Semestre",
        )

        notification = db.add.call_args.args[0]
        assert notification.link == "/docentes/9?period=2024%20Primer%20Semestre"

    @patch("api.utils.evaluation_processor.notification_manager")
    def test_no_link_when_comment_has_no_teacher(self, mock_notification_manager):
        mock_notification_manager.broadcast = AsyncMock()
        db = self._make_db()
        comment = self._make_comment(comment_id=3, teacher_id=None)

        _create_high_risk_comment_notification(
            db,
            director_user_id=55,
            evaluation_id=3,
            teacher_name="Ana Gomez",
            comment=comment,
        )

        notification = db.add.call_args.args[0]
        assert notification.link is None

    @patch("api.utils.evaluation_processor.notification_manager")
    def test_truncates_long_comment_text(self, mock_notification_manager):
        mock_notification_manager.broadcast = AsyncMock()
        db = self._make_db()
        long_text = "x" * 250
        comment = self._make_comment(comment_id=2, text=long_text)

        _create_high_risk_comment_notification(
            db,
            director_user_id=55,
            evaluation_id=3,
            teacher_name="Ana Gomez",
            comment=comment,
        )

        notification = db.add.call_args.args[0]
        assert "..." in notification.message
        assert long_text not in notification.message

    @patch("api.utils.evaluation_processor.notification_manager")
    def test_swallows_errors_without_raising(self, mock_notification_manager):
        mock_notification_manager.broadcast = AsyncMock()
        db = MagicMock()
        db.add.side_effect = RuntimeError("db is down")
        comment = self._make_comment()

        # Should not raise despite the underlying failure.
        _create_high_risk_comment_notification(
            db,
            director_user_id=55,
            evaluation_id=3,
            teacher_name="Ana Gomez",
            comment=comment,
        )

        mock_notification_manager.broadcast.assert_not_called()


class TestCreatePlanSuggestionNotification:
    """The aggregated alert raised once an evaluation has been analysed."""

    def _make_db(self, director=None, existing_notification=None):
        """A db whose queries answer the director lookup and the dedup check."""

        db = MagicMock()
        next_id = {"value": 0}

        def fake_flush():
            for call in db.add.call_args_list:
                obj = call.args[0]
                if isinstance(obj, NotificationModel) and obj.id is None:
                    next_id["value"] += 1
                    obj.id = next_id["value"]

        db.flush.side_effect = fake_flush

        queries = {
            DirectorsModel: _FakeQuery(first_result=director),
            NotificationModel: _FakeQuery(first_result=existing_notification),
        }

        db.query.side_effect = lambda model, *_: queries.get(model, _FakeQuery())

        return db

    def _make_evaluation(self, period_code="2025-1"):
        evaluation = MagicMock(spec=EvaluationModel)
        evaluation.id = 3
        evaluation.department_id = 1
        evaluation.academic_period_id = 2
        evaluation.academic_period = MagicMock(code=period_code)

        return evaluation

    def _director(self, user_id=55):
        director = MagicMock(spec=DirectorsModel)
        director.user_id = user_id

        return director

    def _candidate(self, teacher_id=7, name="Ada Lovelace", **overrides):
        candidate = {
            "teacher_id": teacher_id,
            "name": name,
            "below_threshold": True,
            "has_plan": False,
            "high_risk_comment_count": 0,
            "weak_dimensions": [],
            "weak_questions": [],
        }
        candidate.update(overrides)

        return candidate

    @patch("api.utils.evaluation_processor.notification_manager")
    @patch("api.utils.evaluation_processor.ImprovementPlansRepository")
    @patch("api.utils.evaluation_processor._score_threshold", return_value=3.5)
    def test_notifies_the_director_once_for_the_whole_evaluation(
        self, _mock_threshold, mock_repository, mock_notification_manager
    ):
        mock_notification_manager.broadcast = AsyncMock()
        mock_repository.return_value.get_candidates = AsyncMock(
            return_value=[
                self._candidate(teacher_id=7, name="Ada Lovelace"),
                self._candidate(teacher_id=9, name="Grace Hopper"),
            ]
        )
        db = self._make_db(director=self._director())

        _create_plan_suggestion_notification(db, self._make_evaluation())

        db.add.assert_called_once()
        notification = db.add.call_args.args[0]
        assert isinstance(notification, NotificationModel)
        assert notification.user_id == 55
        assert notification.title == PLAN_SUGGESTION_TITLE
        assert notification.type == "warning"
        assert "2 docentes" in notification.message
        assert "Ada Lovelace" in notification.message
        assert "Grace Hopper" in notification.message
        assert notification.link == "/planes/nuevo?period_code=2025-1"

        mock_notification_manager.broadcast.assert_called_once()
        channel, event = mock_notification_manager.broadcast.call_args.args
        assert channel == "notifications:55"
        assert event.link == "/planes/nuevo?period_code=2025-1"

    @patch("api.utils.evaluation_processor.notification_manager")
    @patch("api.utils.evaluation_processor.ImprovementPlansRepository")
    @patch("api.utils.evaluation_processor._score_threshold", return_value=3.5)
    def test_spells_out_the_reason_when_only_one_teacher_is_suggested(
        self, _mock_threshold, mock_repository, mock_notification_manager
    ):
        mock_notification_manager.broadcast = AsyncMock()
        mock_repository.return_value.get_candidates = AsyncMock(
            return_value=[
                self._candidate(
                    below_threshold=False,
                    high_risk_comment_count=2,
                )
            ]
        )
        db = self._make_db(director=self._director())

        _create_plan_suggestion_notification(db, self._make_evaluation())

        notification = db.add.call_args.args[0]
        assert "Ada Lovelace" in notification.message
        assert "2 comentarios de riesgo alto" in notification.message

    @patch("api.utils.evaluation_processor.notification_manager")
    @patch("api.utils.evaluation_processor.ImprovementPlansRepository")
    @patch("api.utils.evaluation_processor._score_threshold", return_value=3.5)
    def test_stays_quiet_when_nobody_needs_a_plan(
        self, _mock_threshold, mock_repository, mock_notification_manager
    ):
        mock_notification_manager.broadcast = AsyncMock()
        mock_repository.return_value.get_candidates = AsyncMock(return_value=[])
        db = self._make_db(director=self._director())

        _create_plan_suggestion_notification(db, self._make_evaluation())

        db.add.assert_not_called()
        mock_notification_manager.broadcast.assert_not_called()

    @patch("api.utils.evaluation_processor.notification_manager")
    @patch("api.utils.evaluation_processor.ImprovementPlansRepository")
    @patch("api.utils.evaluation_processor._score_threshold", return_value=3.5)
    def test_does_not_repeat_the_alert_when_the_analysis_is_re_run(
        self, _mock_threshold, mock_repository, mock_notification_manager
    ):
        mock_notification_manager.broadcast = AsyncMock()
        mock_repository.return_value.get_candidates = AsyncMock(
            return_value=[self._candidate()]
        )
        db = self._make_db(
            director=self._director(),
            existing_notification=MagicMock(spec=NotificationModel),
        )

        _create_plan_suggestion_notification(db, self._make_evaluation())

        db.add.assert_not_called()

    @patch("api.utils.evaluation_processor.notification_manager")
    @patch("api.utils.evaluation_processor.ImprovementPlansRepository")
    @patch("api.utils.evaluation_processor._score_threshold", return_value=3.5)
    def test_skips_a_department_without_a_director(
        self, _mock_threshold, mock_repository, mock_notification_manager
    ):
        mock_notification_manager.broadcast = AsyncMock()
        mock_repository.return_value.get_candidates = AsyncMock(return_value=[])
        db = self._make_db(director=None)

        _create_plan_suggestion_notification(db, self._make_evaluation())

        db.add.assert_not_called()
        mock_repository.return_value.get_candidates.assert_not_awaited()

    @patch("api.utils.evaluation_processor.notification_manager")
    @patch("api.utils.evaluation_processor.ImprovementPlansRepository")
    @patch("api.utils.evaluation_processor._score_threshold", return_value=3.5)
    def test_a_failed_alert_never_undoes_a_finished_analysis(
        self, _mock_threshold, mock_repository, mock_notification_manager
    ):
        mock_notification_manager.broadcast = AsyncMock()
        mock_repository.return_value.get_candidates = AsyncMock(
            side_effect=RuntimeError("db is down")
        )
        db = self._make_db(director=self._director())

        # Should not raise despite the underlying failure.
        _create_plan_suggestion_notification(db, self._make_evaluation())

        db.add.assert_not_called()
        mock_notification_manager.broadcast.assert_not_called()


class TestContractTypeName:
    """Test suite for the contract type stored when a teacher is saved."""

    def test_maps_tc_to_planta(self):
        """Test 'TC' is stored as 'Planta'."""

        assert _contract_type_name("TC") == "Planta"

    def test_maps_ct_to_catedra(self):
        """Test 'CT' is stored as 'Catedra'."""

        assert _contract_type_name("CT") == "Catedra"

    def test_keeps_codes_without_a_known_name(self):
        """Test a code the university has no name for is stored as it comes."""

        assert _contract_type_name("OTC") == "OTC"
        assert _contract_type_name("MTC") == "MTC"

    def test_keeps_none_when_the_pdf_omits_the_contract_type(self):
        """Test an evaluation that omits the contract type stores nothing."""

        assert _contract_type_name(None) is None
        assert _contract_type_name("") is None
