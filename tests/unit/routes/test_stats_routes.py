"""Tests for the stats routes.

What the route layer owns here: role guards (ADMIN/DIRECTOR for the
department-wide reports, DIRECTOR-only for the department's own reports,
open to any authenticated user for the per-teacher ones), the
"director without a department" 400 guard, and mapping a ``None`` from the
controller to a 404.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from api.controllers.stats import get_stats_controller
from api.routes.stats import router
from tests.unit.routes.conftest import DIRECTOR_USER, DOCENTE_USER


@pytest.fixture
def controller():
    """Mock StatsController with every method the routes call."""

    mock = MagicMock()
    for name in (
        "get_department_averages_by_period",
        "get_department_average_with_previous",
        "get_subject_teachers_comparison",
        "get_department_period_range_report",
        "get_department_period_range_subjects",
        "get_teacher_average_with_previous",
        "get_teacher_history",
        "get_teacher_courses_by_period",
        "get_teacher_comments_by_subject",
        "get_teacher_dimension_averages",
        "get_teacher_matrix",
        "get_teacher_performance_ranking",
        "get_teacher_ranking_paginated",
        "get_teacher_vs_department",
        "get_teacher_vs_previous_period",
        "get_grade_distribution",
        "get_subjects",
        "get_subject_teachers",
    ):
        setattr(mock, name, AsyncMock())
    return mock


@pytest.fixture
def client(make_client, controller):
    """Test client for the stats router."""

    return make_client(router, {get_stats_controller: controller})


class TestDepartmentAveragesByPeriod:
    """GET /stats/departments/averages"""

    def test_returns_the_result(self, client, controller):
        controller.get_department_averages_by_period.return_value = [{"a": 1}]

        response = client.get("/stats/departments/averages")

        assert response.status_code == 200
        assert response.json()["data"] == [{"a": 1}]

    def test_for_a_teacher_returns_403(self, client, controller, auth):
        auth.as_user(DOCENTE_USER)

        response = client.get("/stats/departments/averages")

        assert response.status_code == 403


class TestDepartmentAverageWithPrevious:
    """GET /stats/departments/{department_id}/average"""

    def test_returns_the_result(self, client, controller):
        controller.get_department_average_with_previous.return_value = {"a": 1}

        response = client.get(
            "/stats/departments/7/average?academic_period_id=1"
        )

        assert response.status_code == 200

    def test_when_result_is_none_returns_404(self, client, controller):
        controller.get_department_average_with_previous.return_value = None

        response = client.get(
            "/stats/departments/999/average?academic_period_id=1"
        )

        assert response.status_code == 404


class TestSubjectTeachersComparison:
    """GET /stats/departments/subjects/{course_code}/teachers-comparison"""

    def test_for_the_directors_own_department_returns_200(
        self, client, controller, auth
    ):
        auth.as_user(DIRECTOR_USER)
        controller.get_subject_teachers_comparison.return_value = [{"a": 1}]

        response = client.get(
            "/stats/departments/subjects/BD101/teachers-comparison?period=2026-1"
        )

        assert response.status_code == 200
        controller.get_subject_teachers_comparison.assert_awaited_once_with(
            DIRECTOR_USER["department_id"], "BD101", "2026-1"
        )

    def test_for_a_director_without_department_returns_400(
        self, client, controller, auth
    ):
        auth.as_user({**DIRECTOR_USER, "department_id": None})

        response = client.get(
            "/stats/departments/subjects/BD101/teachers-comparison?period=2026-1"
        )

        assert response.status_code == 400

    def test_for_an_admin_returns_403(self, client, controller, auth):
        response = client.get(
            "/stats/departments/subjects/BD101/teachers-comparison?period=2026-1"
        )

        assert response.status_code == 403


class TestDepartmentPeriodRangeReport:
    """GET /stats/departments/period-range"""

    def test_for_the_director_returns_200(self, client, controller, auth):
        auth.as_user(DIRECTOR_USER)
        controller.get_department_period_range_report.return_value = {"a": 1}

        response = client.get(
            "/stats/departments/period-range?start_period=2020-1&end_period=2022-1"
        )

        assert response.status_code == 200

    def test_when_result_is_none_returns_404(self, client, controller, auth):
        auth.as_user(DIRECTOR_USER)
        controller.get_department_period_range_report.return_value = None

        response = client.get(
            "/stats/departments/period-range?start_period=2020-1&end_period=2022-1"
        )

        assert response.status_code == 404

    def test_for_a_director_without_department_returns_400(
        self, client, controller, auth
    ):
        auth.as_user({**DIRECTOR_USER, "department_id": None})

        response = client.get(
            "/stats/departments/period-range?start_period=2020-1&end_period=2022-1"
        )

        assert response.status_code == 400


class TestDepartmentPeriodRangeSubjects:
    """GET /stats/departments/period-range/subjects"""

    def test_for_the_director_returns_200(self, client, controller, auth):
        auth.as_user(DIRECTOR_USER)
        controller.get_department_period_range_subjects.return_value = [{"a": 1}]

        response = client.get(
            "/stats/departments/period-range/subjects"
            "?start_period=2020-1&end_period=2022-1"
        )

        assert response.status_code == 200

    def test_when_result_is_none_returns_404(self, client, controller, auth):
        auth.as_user(DIRECTOR_USER)
        controller.get_department_period_range_subjects.return_value = None

        response = client.get(
            "/stats/departments/period-range/subjects"
            "?start_period=2020-1&end_period=2022-1"
        )

        assert response.status_code == 404

    def test_for_a_director_without_department_returns_400(
        self, client, controller, auth
    ):
        auth.as_user({**DIRECTOR_USER, "department_id": None})

        response = client.get(
            "/stats/departments/period-range/subjects"
            "?start_period=2020-1&end_period=2022-1"
        )

        assert response.status_code == 400


class TestTeacherAverageWithPrevious:
    """GET /stats/teachers/{teacher_id}/average"""

    def test_returns_the_result(self, client, controller):
        controller.get_teacher_average_with_previous.return_value = {"a": 1}

        response = client.get("/stats/teachers/1/average?academic_period_id=1")

        assert response.status_code == 200

    def test_when_result_is_none_returns_404(self, client, controller):
        controller.get_teacher_average_with_previous.return_value = None

        response = client.get("/stats/teachers/999/average?academic_period_id=1")

        assert response.status_code == 404


class TestTeacherHistory:
    """GET /stats/teachers/{teacher_id}/history"""

    def test_returns_the_result(self, client, controller):
        controller.get_teacher_history.return_value = [{"a": 1}]

        response = client.get("/stats/teachers/1/history")

        assert response.status_code == 200

    def test_when_result_is_none_returns_404(self, client, controller):
        controller.get_teacher_history.return_value = None

        response = client.get("/stats/teachers/999/history")

        assert response.status_code == 404


class TestTeacherCourses:
    """GET /stats/teachers/{teacher_id}/courses"""

    def test_returns_the_result(self, client, controller):
        controller.get_teacher_courses_by_period.return_value = [{"a": 1}]

        response = client.get("/stats/teachers/1/courses?academic_period_id=1")

        assert response.status_code == 200

    def test_when_result_is_none_returns_404(self, client, controller):
        controller.get_teacher_courses_by_period.return_value = None

        response = client.get("/stats/teachers/999/courses?academic_period_id=1")

        assert response.status_code == 404


class TestTeacherCommentsBySubject:
    """GET /stats/teachers/{teacher_id}/comments"""

    def test_returns_the_result(self, client, controller):
        controller.get_teacher_comments_by_subject.return_value = {"a": 1}

        response = client.get("/stats/teachers/1/comments?academic_period_id=1")

        assert response.status_code == 200

    def test_when_result_is_none_returns_404(self, client, controller):
        controller.get_teacher_comments_by_subject.return_value = None

        response = client.get("/stats/teachers/999/comments?academic_period_id=1")

        assert response.status_code == 404


class TestTeacherDimensionAverages:
    """GET /stats/teachers/{teacher_id}/dimensions"""

    def test_returns_the_result(self, client, controller):
        controller.get_teacher_dimension_averages.return_value = {"a": 1}

        response = client.get("/stats/teachers/1/dimensions?academic_period_id=1")

        assert response.status_code == 200

    def test_when_result_is_none_returns_404(self, client, controller):
        controller.get_teacher_dimension_averages.return_value = None

        response = client.get("/stats/teachers/999/dimensions?academic_period_id=1")

        assert response.status_code == 404


class TestTeacherMatrix:
    """GET /stats/teachers/{teacher_id}/matrix"""

    def test_returns_the_result(self, client, controller):
        controller.get_teacher_matrix.return_value = {"a": 1}

        response = client.get("/stats/teachers/1/matrix?evaluation_id=1")

        assert response.status_code == 200

    def test_when_result_is_none_returns_404(self, client, controller):
        controller.get_teacher_matrix.return_value = None

        response = client.get("/stats/teachers/999/matrix?evaluation_id=1")

        assert response.status_code == 404


class TestTeacherPerformanceRanking:
    """GET /stats/teachers/ranking"""

    def test_returns_the_result(self, client, controller):
        controller.get_teacher_performance_ranking.return_value = {"top_5": []}

        response = client.get("/stats/teachers/ranking")

        assert response.status_code == 200

    def test_for_a_teacher_returns_403(self, client, controller, auth):
        auth.as_user(DOCENTE_USER)

        response = client.get("/stats/teachers/ranking")

        assert response.status_code == 403


class TestTeacherRankingPaginated:
    """GET /stats/teachers/ranking/paginated"""

    def test_returns_the_result(self, client, controller):
        controller.get_teacher_ranking_paginated.return_value = {"items": []}

        response = client.get("/stats/teachers/ranking/paginated")

        assert response.status_code == 200
        controller.get_teacher_ranking_paginated.assert_awaited_once_with(
            academic_period_id=None,
            department_id=None,
            page=1,
            limit=10,
            search=None,
            sort="desc",
        )


class TestTeacherVsDepartment:
    """GET /stats/teachers/{teacher_id}/comparison"""

    def test_returns_the_result(self, client, controller):
        controller.get_teacher_vs_department.return_value = {"a": 1}

        response = client.get("/stats/teachers/1/comparison?academic_period_id=1")

        assert response.status_code == 200

    def test_when_result_is_none_returns_404(self, client, controller):
        controller.get_teacher_vs_department.return_value = None

        response = client.get("/stats/teachers/999/comparison?academic_period_id=1")

        assert response.status_code == 404


class TestTeacherVsPreviousPeriod:
    """GET /stats/teachers/{teacher_id}/period-comparison"""

    def test_returns_the_result(self, client, controller):
        controller.get_teacher_vs_previous_period.return_value = {"a": 1}

        response = client.get(
            "/stats/teachers/1/period-comparison?academic_period_id=1"
        )

        assert response.status_code == 200

    def test_when_result_is_none_returns_404(self, client, controller):
        controller.get_teacher_vs_previous_period.return_value = None

        response = client.get(
            "/stats/teachers/999/period-comparison?academic_period_id=1"
        )

        assert response.status_code == 404


class TestGradeDistribution:
    """GET /stats/distribution/grades"""

    def test_returns_the_result(self, client, controller):
        controller.get_grade_distribution.return_value = {"bins": []}

        response = client.get("/stats/distribution/grades")

        assert response.status_code == 200
        controller.get_grade_distribution.assert_awaited_once_with(None, None, 0.5)

    def test_for_a_teacher_returns_403(self, client, controller, auth):
        auth.as_user(DOCENTE_USER)

        response = client.get("/stats/distribution/grades")

        assert response.status_code == 403


class TestSubjectsAnalytics:
    """GET /stats/subjects/analytics"""

    def test_returns_the_result(self, client, controller):
        controller.get_subjects.return_value = [{"a": 1}]

        response = client.get("/stats/subjects/analytics?academic_period_id=1")

        assert response.status_code == 200

    def test_for_a_teacher_returns_403(self, client, controller, auth):
        auth.as_user(DOCENTE_USER)

        response = client.get("/stats/subjects/analytics?academic_period_id=1")

        assert response.status_code == 403


class TestSubjectTeachers:
    """GET /stats/subjects/{course_id}/teachers"""

    def test_returns_the_result(self, client, controller):
        controller.get_subject_teachers.return_value = {"a": 1}

        response = client.get("/stats/subjects/1/teachers?academic_period_id=1")

        assert response.status_code == 200

    def test_when_result_is_none_returns_404(self, client, controller):
        controller.get_subject_teachers.return_value = None

        response = client.get("/stats/subjects/999/teachers?academic_period_id=1")

        assert response.status_code == 404

    def test_for_a_teacher_returns_403(self, client, controller, auth):
        auth.as_user(DOCENTE_USER)

        response = client.get("/stats/subjects/1/teachers?academic_period_id=1")

        assert response.status_code == 403
