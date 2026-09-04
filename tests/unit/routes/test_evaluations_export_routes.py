"""Tests for the evaluation Excel export routes.

Both stream a file built by ``api.utils.*_excel_export``; the route's own job
is fetching the data (through the controller, or a raw query for the
department-vs-average comparison) and turning a miss into a 404 before any of
that runs.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from api.controllers.evaluations import get_evaluations_controller
from api.database import get_db
from api.repositories.stats import get_stats_repository
from api.routes.evaluations import router
from tests.unit.routes.conftest import DOCENTE_USER

TEACHER_DETAIL = {"evaluation_id": 1, "teacher_id": 5, "courses": []}
SUMMARY = {"id": 1, "department_id": 7}


@pytest.fixture
def controller():
    mock = MagicMock()
    mock.get_teacher_detail = AsyncMock()
    mock.get_teacher_comments = AsyncMock()
    mock.get_summary = AsyncMock()
    return mock


@pytest.fixture
def mock_db():
    return MagicMock()


@pytest.fixture
def mock_stats_repo():
    repo = MagicMock()
    repo.get_teacher_vs_department = AsyncMock(return_value=None)
    return repo


@pytest.fixture
def client(make_client, controller, mock_db, mock_stats_repo):
    return make_client(
        router,
        {
            get_evaluations_controller: controller,
            get_db: mock_db,
            get_stats_repository: mock_stats_repo,
        },
    )


class TestExportTeacherEvaluation:
    """GET /evaluations/teachers/{teacher_id}/export"""

    def test_when_missing_returns_404(self, client, controller):
        controller.get_teacher_detail.return_value = None

        response = client.get(
            "/evaluations/teachers/5/export"
            "?period_name=2026-1&department_id=7"
        )

        assert response.status_code == 404

    def test_streams_the_report(self, client, controller, mock_db, mock_stats_repo):
        controller.get_teacher_detail.return_value = TEACHER_DETAIL
        mock_db.query.return_value.filter.return_value.first.return_value = (
            MagicMock(academic_period_id=1)
        )
        mock_stats_repo.get_teacher_vs_department.return_value = {"a": 1}

        with patch(
            "api.routes.evaluations.build_teacher_report",
            return_value=(b"excel-bytes", "reporte.xlsx"),
        ) as build, patch(
            "api.routes.evaluations.teacher_streaming_response"
        ) as stream:
            from fastapi.responses import Response

            stream.return_value = Response(content=b"excel-bytes")

            response = client.get(
                "/evaluations/teachers/5/export"
                "?period_name=2026-1&department_id=7"
            )

        assert response.status_code == 200
        build.assert_called_once()

    def test_includes_comments_when_requested(
        self, client, controller, mock_db, mock_stats_repo
    ):
        controller.get_teacher_detail.return_value = TEACHER_DETAIL
        controller.get_teacher_comments.return_value = {
            "courses": [
                {
                    "course_code": "BD101",
                    "course_name": "Bases de Datos",
                    "comments": ["Excelente"],
                }
            ]
        }
        mock_db.query.return_value.filter.return_value.first.return_value = None

        with patch(
            "api.routes.evaluations.build_teacher_report",
            return_value=(b"excel-bytes", "reporte.xlsx"),
        ) as build, patch(
            "api.routes.evaluations.teacher_streaming_response"
        ) as stream:
            from fastapi.responses import Response

            stream.return_value = Response(content=b"excel-bytes")

            response = client.get(
                "/evaluations/teachers/5/export"
                "?period_name=2026-1&department_id=7&include_comments=true"
            )

        assert response.status_code == 200
        comments_by_course = build.call_args.args[2]
        assert comments_by_course == {"BD101 - Bases de Datos": ["Excelente"]}

    def test_for_a_teacher_returns_403(self, client, controller, auth):
        auth.as_user(DOCENTE_USER)

        response = client.get(
            "/evaluations/teachers/5/export"
            "?period_name=2026-1&department_id=7"
        )

        assert response.status_code == 403
        controller.get_teacher_detail.assert_not_called()


class TestExportEvaluation:
    """GET /evaluations/{evaluation_id}/export"""

    def test_when_missing_returns_404(self, client, controller):
        controller.get_summary.return_value = None

        response = client.get("/evaluations/999/export")

        assert response.status_code == 404

    def test_streams_the_report(self, client, controller):
        controller.get_summary.return_value = SUMMARY

        with patch(
            "api.routes.evaluations.build_evaluation_report",
            return_value=(b"excel-bytes", "resumen.xlsx"),
        ) as build, patch(
            "api.routes.evaluations.evaluation_streaming_response"
        ) as stream:
            from fastapi.responses import Response

            stream.return_value = Response(content=b"excel-bytes")

            response = client.get("/evaluations/1/export")

        assert response.status_code == 200
        build.assert_called_once_with(SUMMARY)

    def test_for_a_teacher_returns_403(self, client, controller, auth):
        auth.as_user(DOCENTE_USER)

        response = client.get("/evaluations/1/export")

        assert response.status_code == 403
        controller.get_summary.assert_not_called()
