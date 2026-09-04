"""Tests for the courses routes.

What the route layer owns here: ADMIN-only for most mutations, the
director-scoped name patch (which needs a department on the caller before it
even reaches the controller), and mapping a ``None`` from the controller to
a 404.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from api.controllers.courses import get_courses_controller
from api.routes.courses import router
from tests.unit.routes.conftest import DIRECTOR_USER, DOCENTE_USER, paginated

COURSE = {
    "id": 1,
    "code": "BD101",
    "name": "Bases de Datos",
    "department_id": 7,
    "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-01-01T00:00:00Z",
}


@pytest.fixture
def controller():
    """Mock CoursesController."""

    mock = MagicMock()
    mock.get_all = AsyncMock()
    mock.get_by_id = AsyncMock()
    mock.create = AsyncMock()
    mock.update = AsyncMock()
    mock.update_name = AsyncMock()
    mock.delete = AsyncMock()
    return mock


@pytest.fixture
def client(make_client, controller):
    """Test client for the courses router."""

    return make_client(router, {get_courses_controller: controller})


class TestListCourses:
    """GET /courses/"""

    def test_returns_items_and_pagination(self, client, controller):
        """Test the paginated dict is split into data and pagination."""

        controller.get_all.return_value = paginated([COURSE])

        response = client.get("/courses/")

        assert response.status_code == 200
        assert response.json()["data"] == [COURSE]

    def test_for_a_director_returns_403(self, client, controller, auth):
        """Test a director cannot list all courses."""

        auth.as_user(DIRECTOR_USER)

        response = client.get("/courses/")

        assert response.status_code == 403


class TestCreateCourse:
    """POST /courses/"""

    def test_with_valid_payload_returns_201(self, client, controller):
        """Test a valid payload creates the course."""

        controller.create.return_value = COURSE

        response = client.post("/courses/", json={"code": "BD101"})

        assert response.status_code == 201


class TestGetCourse:
    """GET /courses/{course_id}"""

    def test_when_course_exists_returns_200(self, client, controller):
        """Test an existing course is returned."""

        controller.get_by_id.return_value = COURSE

        response = client.get("/courses/1")

        assert response.status_code == 200

    def test_when_course_missing_returns_404(self, client, controller):
        """Test a None from the controller becomes a 404."""

        controller.get_by_id.return_value = None

        response = client.get("/courses/999")

        assert response.status_code == 404


class TestPatchCourseName:
    """PATCH /courses/{course_id}/name"""

    def test_for_the_courses_own_director_returns_200(self, client, controller, auth):
        """Test the director's own department reaches the controller."""

        auth.as_user(DIRECTOR_USER)
        controller.update_name.return_value = {**COURSE, "name": "Redes"}

        response = client.patch("/courses/1/name", json={"name": "Redes"})

        assert response.status_code == 200
        controller.update_name.assert_called_once_with(
            1, "Redes", DIRECTOR_USER["department_id"], DIRECTOR_USER
        )

    def test_when_course_missing_returns_404(self, client, controller, auth):
        """Test a None from the controller becomes a 404."""

        auth.as_user(DIRECTOR_USER)
        controller.update_name.return_value = None

        response = client.patch("/courses/999/name", json={"name": "Redes"})

        assert response.status_code == 404

    def test_for_a_director_without_department_returns_400(
        self, client, controller, auth
    ):
        """Test a director with no assigned department is rejected."""

        auth.as_user({**DIRECTOR_USER, "department_id": None})

        response = client.patch("/courses/1/name", json={"name": "Redes"})

        assert response.status_code == 400
        controller.update_name.assert_not_called()

    def test_for_a_teacher_returns_403(self, client, controller, auth):
        """Test a teacher cannot patch a course name."""

        auth.as_user(DOCENTE_USER)

        response = client.patch("/courses/1/name", json={"name": "Redes"})

        assert response.status_code == 403


class TestUpdateCourse:
    """PUT /courses/{course_id}"""

    def test_with_valid_payload_returns_200(self, client, controller):
        """Test a valid payload updates the course."""

        controller.update.return_value = {**COURSE, "name": "Redes"}

        response = client.put("/courses/1", json={"name": "Redes"})

        assert response.status_code == 200

    def test_when_course_missing_returns_404(self, client, controller):
        """Test a None from the controller becomes a 404."""

        controller.update.return_value = None

        response = client.put("/courses/999", json={"name": "Redes"})

        assert response.status_code == 404


class TestDeleteCourse:
    """DELETE /courses/{course_id}"""

    def test_when_course_exists_returns_200(self, client, controller):
        """Test deleting an existing course returns it."""

        controller.delete.return_value = COURSE

        response = client.delete("/courses/1")

        assert response.status_code == 200

    def test_when_course_missing_returns_404(self, client, controller):
        """Test a None from the controller becomes a 404."""

        controller.delete.return_value = None

        response = client.delete("/courses/999")

        assert response.status_code == 404
