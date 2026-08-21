"""
Tests for the teacher routes.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from api.controllers.teachers import get_teachers_controller
from api.routes.teachers import router
from tests.unit.routes.conftest import (
    ADMIN_USER,
    DIRECTOR_USER,
    DOCENTE_USER,
    paginated,
)

TEACHER = {
    "id": 5,
    "institutional_code": "1234",
    "department_id": 7,
    "contract_type": "TIEMPO COMPLETO",
    "user_id": 3,
    "active": True,
}


@pytest.fixture
def controller():
    """Mock TeachersController."""

    mock = MagicMock()
    mock.get_all = AsyncMock()
    mock.get_all_with_averages = AsyncMock()
    mock.update = AsyncMock()
    mock.get_history = AsyncMock()
    mock.get_evaluation_report = AsyncMock()
    return mock


@pytest.fixture
def client(make_client, controller):
    """Test client for the teachers router."""

    return make_client(router, {get_teachers_controller: controller})


class TestGetAllTeachers:
    """Test suite for GET /teachers/."""

    async def test_returns_the_paginated_envelope(self, client, controller):
        """The paginated dict is split into `data` and `pagination`."""

        controller.get_all.return_value = paginated([TEACHER], total=1)

        response = client.get("/teachers/")

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "success"
        assert body["data"] == [TEACHER]
        assert body["pagination"] == {"total": 1, "page": 1, "limit": 10, "pages": 1}

    async def test_forwards_filters_and_pagination(self, client, controller):
        """Query parameters reach the controller as filters and pagination."""

        controller.get_all.return_value = paginated([], page=2, limit=25)

        response = client.get(
            "/teachers/",
            params={
                "search": "perez",
                "active": "true",
                "department_id": 9,
                "contract_type": "CATEDRA",
                "sort_by": "name",
                "page": 2,
                "limit": 25,
            },
        )

        assert response.status_code == 200
        filters, pagination = controller.get_all.call_args.args
        assert filters.search == "perez"
        assert filters.active is True
        assert filters.department_id == 9
        assert filters.contract_type == "CATEDRA"
        assert filters.sort_by == "name"
        assert (pagination.page, pagination.limit) == (2, 25)

    async def test_director_is_scoped_to_their_own_department(
        self, client, controller, auth
    ):
        """A director's department_id from the token overrides the query one."""

        auth.as_user(DIRECTOR_USER)
        controller.get_all.return_value = paginated([])

        response = client.get("/teachers/", params={"department_id": 99})

        assert response.status_code == 200
        filters, _ = controller.get_all.call_args.args
        assert filters.department_id == DIRECTOR_USER["department_id"]

    async def test_director_without_department_gets_an_empty_page(
        self, client, controller, auth
    ):
        """No department on the token short-circuits to an empty page."""

        auth.as_user({**DIRECTOR_USER, "department_id": None})

        response = client.get("/teachers/")

        assert response.status_code == 200
        body = response.json()
        assert body["data"] == []
        assert body["pagination"] == {"total": 0, "page": 1, "limit": 10, "pages": 0}
        controller.get_all.assert_not_called()

    async def test_docente_is_forbidden(self, client, controller, auth):
        """DOCENTE is not in the allowed roles for the listing."""

        auth.as_user(DOCENTE_USER)

        response = client.get("/teachers/")

        assert response.status_code == 403
        controller.get_all.assert_not_called()

    async def test_requires_authentication(self, client, controller, auth):
        """Without a token the request is rejected."""

        auth.anonymous()

        response = client.get("/teachers/")

        assert response.status_code == 401
        controller.get_all.assert_not_called()

    async def test_rejects_a_limit_over_the_maximum(self, client, controller):
        """The pagination dependency caps limit at 100."""

        response = client.get("/teachers/", params={"limit": 101})

        assert response.status_code == 422
        assert response.json()["error"]["code"] == "VALIDATION_ERROR"
        controller.get_all.assert_not_called()


class TestGetTeachersWithAverages:
    """Test suite for GET /teachers/with-averages."""

    async def test_forwards_period_and_defaults(self, client, controller):
        """academic_period_id is forwarded, has_average defaults to True."""

        controller.get_all_with_averages.return_value = paginated([TEACHER], total=1)

        response = client.get("/teachers/with-averages", params={"academic_period_id": 4})

        assert response.status_code == 200
        assert response.json()["data"] == [TEACHER]
        _, _, period_id, has_average, modality = (
            controller.get_all_with_averages.call_args.args
        )
        assert period_id == 4
        assert has_average is True
        assert modality is None

    async def test_forwards_modality_and_has_average(self, client, controller):
        """Both optional flags reach the controller as given."""

        controller.get_all_with_averages.return_value = paginated([])

        response = client.get(
            "/teachers/with-averages",
            params={
                "academic_period_id": 4,
                "has_average": "false",
                "modality": "DISTANCIA",
            },
        )

        assert response.status_code == 200
        _, _, _, has_average, modality = (
            controller.get_all_with_averages.call_args.args
        )
        assert has_average is False
        assert modality == "DISTANCIA"

    async def test_rejects_an_unknown_modality(self, client, controller):
        """Only the catalogued modalities are accepted."""

        response = client.get(
            "/teachers/with-averages",
            params={"academic_period_id": 4, "modality": "VIRTUAL"},
        )

        assert response.status_code == 422
        controller.get_all_with_averages.assert_not_called()

    async def test_requires_the_academic_period(self, client, controller):
        """academic_period_id has no default."""

        response = client.get("/teachers/with-averages")

        assert response.status_code == 422
        controller.get_all_with_averages.assert_not_called()

    async def test_director_is_scoped_to_their_own_department(
        self, client, controller, auth
    ):
        """A director's department_id from the token overrides the query one."""

        auth.as_user(DIRECTOR_USER)
        controller.get_all_with_averages.return_value = paginated([])

        response = client.get(
            "/teachers/with-averages",
            params={"academic_period_id": 4, "department_id": 99},
        )

        assert response.status_code == 200
        filters = controller.get_all_with_averages.call_args.args[0]
        assert filters.department_id == DIRECTOR_USER["department_id"]

    async def test_director_without_department_gets_an_empty_page(
        self, client, controller, auth
    ):
        """No department on the token short-circuits to an empty page."""

        auth.as_user({**DIRECTOR_USER, "department_id": None})

        response = client.get(
            "/teachers/with-averages", params={"academic_period_id": 4}
        )

        assert response.status_code == 200
        assert response.json()["data"] == []
        controller.get_all_with_averages.assert_not_called()

    async def test_docente_is_forbidden(self, client, controller, auth):
        """DOCENTE is not in the allowed roles for the listing."""

        auth.as_user(DOCENTE_USER)

        response = client.get(
            "/teachers/with-averages", params={"academic_period_id": 4}
        )

        assert response.status_code == 403
        controller.get_all_with_averages.assert_not_called()


class TestUpdateTeacher:
    """Test suite for PUT /teachers/{teacher_id}."""

    async def test_updates_and_returns_the_teacher(self, client, controller):
        """The payload and the acting user are forwarded to the controller."""

        controller.update.return_value = {**TEACHER, "contract_type": "CATEDRA"}

        response = client.put(
            "/teachers/5", json={"contract_type": "CATEDRA", "active": True}
        )

        assert response.status_code == 200
        assert response.json()["data"]["contract_type"] == "CATEDRA"
        teacher_id, payload, current_user = controller.update.call_args.args
        assert teacher_id == 5
        assert payload.contract_type == "CATEDRA"
        assert payload.active is True
        assert current_user["uid"] == ADMIN_USER["uid"]

    async def test_returns_404_when_the_teacher_does_not_exist(
        self, client, controller
    ):
        """A None from the controller becomes a 404."""

        controller.update.return_value = None

        response = client.put("/teachers/999", json={"contract_type": "CATEDRA"})

        assert response.status_code == 404
        assert response.json()["error"]["message"] == "Teacher not found"

    async def test_rejects_a_non_numeric_institutional_code(self, client, controller):
        """The schema validator rejects a code that is not an integer."""

        response = client.put("/teachers/5", json={"institutional_code": "12.5"})

        assert response.status_code == 422
        controller.update.assert_not_called()

    async def test_docente_is_forbidden(self, client, controller, auth):
        """Only ADMIN and DIRECTOR may update a teacher."""

        auth.as_user(DOCENTE_USER)

        response = client.put("/teachers/5", json={"contract_type": "CATEDRA"})

        assert response.status_code == 403
        controller.update.assert_not_called()


class TestGetTeacherHistory:
    """Test suite for GET /teachers/{teacher_id}/history."""

    async def test_returns_the_history(self, client, controller):
        """The controller result is returned inside the envelope."""

        history = {"teacher_id": 5, "periods": [{"period": "2025-1", "average": 4.2}]}
        controller.get_history.return_value = history

        response = client.get("/teachers/5/history")

        assert response.status_code == 200
        assert response.json()["data"] == history

    async def test_forwards_the_current_user_pagination_and_sort(
        self, client, controller
    ):
        """sort_by comes from the teacher filters, not from a dedicated param."""

        controller.get_history.return_value = {"periods": []}

        response = client.get(
            "/teachers/5/history", params={"sort_by": "period", "page": 3, "limit": 5}
        )

        assert response.status_code == 200
        current_user, teacher_id, pagination, sort_by = (
            controller.get_history.call_args.args
        )
        assert current_user.uid == ADMIN_USER["uid"]
        assert teacher_id == 5
        assert (pagination.page, pagination.limit) == (3, 5)
        assert sort_by == "period"

    async def test_returns_404_when_there_is_no_history(self, client, controller):
        """An empty result from the controller becomes a 404."""

        controller.get_history.return_value = None

        response = client.get("/teachers/999/history")

        assert response.status_code == 404
        assert response.json()["error"]["message"] == "Teacher not found"

    async def test_docente_may_read_the_history(self, client, controller, auth):
        """DOCENTE is among the roles allowed on this endpoint."""

        auth.as_user(DOCENTE_USER)
        controller.get_history.return_value = {"periods": []}

        response = client.get("/teachers/5/history")

        assert response.status_code == 200

    async def test_requires_authentication(self, client, controller, auth):
        """Without a token the request is rejected."""

        auth.anonymous()

        response = client.get("/teachers/5/history")

        assert response.status_code == 401
        controller.get_history.assert_not_called()


class TestDownloadTeacherEvaluationReport:
    """Test suite for GET /teachers/{id}/evaluations/{id}/report."""

    async def test_streams_the_pdf_outside_the_envelope(
        self, client, controller, auth
    ):
        """The PDF bytes are streamed as-is, not wrapped by the middleware."""

        auth.as_user(DIRECTOR_USER)
        controller.get_evaluation_report.return_value = b"%PDF-1.7 fake"

        response = client.get("/teachers/5/evaluations/12/report")

        assert response.status_code == 200
        assert response.content == b"%PDF-1.7 fake"
        assert response.headers["content-type"] == "application/pdf"
        assert (
            response.headers["content-disposition"]
            == 'inline; filename="evaluacion_docente_5.pdf"'
        )

    async def test_forwards_both_ids_and_the_current_user(
        self, client, controller, auth
    ):
        """The service needs the token user to authorize the download."""

        auth.as_user(DOCENTE_USER)
        controller.get_evaluation_report.return_value = b"%PDF-1.7"

        client.get("/teachers/5/evaluations/12/report")

        teacher_id, evaluation_id, current_user = (
            controller.get_evaluation_report.call_args.args
        )
        assert (teacher_id, evaluation_id) == (5, 12)
        assert current_user.uid == DOCENTE_USER["uid"]

    async def test_returns_404_when_the_report_is_missing(
        self, client, controller, auth
    ):
        """A None from the controller becomes a 404 with a Spanish message."""

        auth.as_user(DIRECTOR_USER)
        controller.get_evaluation_report.return_value = None

        response = client.get("/teachers/5/evaluations/12/report")

        assert response.status_code == 404
        assert "no encontrado" in response.json()["error"]["message"]

    async def test_admin_is_forbidden(self, client, controller, auth):
        """Only DOCENTE and DIRECTOR may download a teacher report."""

        auth.as_user(ADMIN_USER)

        response = client.get("/teachers/5/evaluations/12/report")

        assert response.status_code == 403
        controller.get_evaluation_report.assert_not_called()
