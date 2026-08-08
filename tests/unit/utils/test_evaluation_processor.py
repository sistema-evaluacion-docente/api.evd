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
from api.models.director import DirectorsModel
from api.models.evaluation import EvaluationModel
from api.models.notification import NotificationModel
from api.models.pedagogical_category import PedagogicalCategoryModel
from api.models.risk_level import RiskLevelModel
from api.models.teacher import TeacherModel
from api.utils.evaluation_processor import (
    HIGH_RISK_LEVEL_ID,
    _create_high_risk_comment_notification,
    analyze_evaluation_comments,
)


def _risk_level(level_id: int, name: str) -> MagicMock:
    risk_level = MagicMock()
    risk_level.id = level_id
    risk_level.name = name
    return risk_level


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

    def _make_evaluation(self, department_id=1):
        evaluation = MagicMock(spec=EvaluationModel)
        evaluation.id = 1
        evaluation.department_id = department_id
        evaluation.user_id = 99
        return evaluation

    def _make_comment(self, comment_id, teacher_id, text="Comentario de prueba"):
        comment = MagicMock(spec=CommentModel)
        comment.id = comment_id
        comment.teacher_id = teacher_id
        comment.original_text = text
        comment.risk_level = None
        comment.risk_score = None
        comment.pedagogical_category_id = None
        comment.category_score = None
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
            "category_label": None,
            "category_score": None,
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
            "category_label": None,
            "category_score": None,
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
            "category_label": None,
            "category_score": None,
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
            "category_label": None,
            "category_score": None,
        }
        mock_notification_manager.broadcast = AsyncMock()

        analyze_evaluation_comments(evaluation.id)

        teacher_query_calls = [
            call for call in db.query.call_args_list if call.args[0] is TeacherModel
        ]
        assert len(teacher_query_calls) == 1
        assert len(_added_notifications(db, "Alerta: comentario de riesgo alto")) == 2


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

    def _make_comment(self, comment_id=1, text="Comentario"):
        comment = MagicMock(spec=CommentModel)
        comment.id = comment_id
        comment.original_text = text
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

        db.flush.assert_called_once()
        mock_notification_manager.broadcast.assert_called_once()
        channel, event = mock_notification_manager.broadcast.call_args.args
        assert channel == "notifications:55"
        assert event.user_id == 55
        assert event.notification_type == "warning"

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
