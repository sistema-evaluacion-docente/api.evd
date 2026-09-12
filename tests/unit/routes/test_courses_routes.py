"""Tests for the courses routes.

What the route layer owns here: DIRECTOR-only for the whole resource,
resolving the caller's own department before it even reaches the controller
(rejecting a director with no department assigned), and mapping a ``None``
from the controller to a 404.
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

    def test_for_the_directors_own_department_returns_items_and_pagination(
        self, client, controller, auth
    ):
        """Test the paginated dict is split into data and pagination."""

        auth.as_user(DIRECTOR_USER)
        controller.get_all.return_value = paginated([COURSE])

        response = client.get("/courses/")

        assert response.status_code == 200
        assert response.json()["data"] == [COURSE]
        controller.get_all.assert_called_once()
        assert controller.get_all.call_args[0][2] == DIRECTOR_USER["department_id"]

    def test_for_an_admin_returns_403(self, client, controller):
        """Test an ADMIN cannot list courses — this resource is director-only."""

        response = client.get("/courses/")

        assert response.status_code == 403

    def test_for_a_director_without_department_returns_400(
        self, client, controller, auth
    ):
        """Test a director with no assigned department is rejected."""

        auth.as_user({**DIRECTOR_USER, "department_id": None})

        response = client.get("/courses/")

        assert response.status_code == 400
        controller.get_all.assert_not_called()


class TestCreateCourse:
    """POST /courses/"""

    def test_for_the_directors_own_department_returns_201(
        self, client, controller, auth
    ):
        """Test a valid payload creates the course in the director's department."""

        auth.as_user(DIRECTOR_USER)
        controller.create.return_value = COURSE

        response = client.post("/courses/", json={"code": "BD101"})

        assert response.status_code == 201
        controller.create.assert_called_once()
        assert controller.create.call_args[0][1] == DIRECTOR_USER["department_id"]

    def test_for_an_admin_returns_403(self, client, controller):
        """Test an ADMIN cannot create a course."""

        response = client.post("/courses/", json={"code": "BD101"})

        assert response.status_code == 403


class TestGetCourse:
    """GET /courses/{course_id}"""

    def test_when_course_exists_returns_200(self, client, controller, auth):
        """Test an existing course is returned."""

        auth.as_user(DIRECTOR_USER)
        controller.get_by_id.return_value = COURSE

        response = client.get("/courses/1")

        assert response.status_code == 200
        controller.get_by_id.assert_called_once_with(1, DIRECTOR_USER["department_id"])

    def test_when_course_missing_returns_404(self, client, controller, auth):
        """Test a None from the controller becomes a 404."""

        auth.as_user(DIRECTOR_USER)
        controller.get_by_id.return_value = None

        response = client.get("/courses/999")

        assert response.status_code == 404

    def test_for_an_admin_returns_403(self, client, controller):
        """Test an ADMIN cannot get a course by id."""

        response = client.get("/courses/1")

        assert response.status_code == 403

    def test_for_a_teacher_returns_403(self, client, controller, auth):
        """Test a teacher cannot get a course by id."""

        auth.as_user(DOCENTE_USER)

        response = client.get("/courses/1")

        assert response.status_code == 403


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

    def test_for_an_admin_returns_403(self, client, controller):
        """Test an ADMIN cannot patch a course name."""

        response = client.patch("/courses/1/name", json={"name": "Redes"})

        assert response.status_code == 403

    def test_for_a_teacher_returns_403(self, client, controller, auth):
        """Test a teacher cannot patch a course name."""

        auth.as_user(DOCENTE_USER)

        response = client.patch("/courses/1/name", json={"name": "Redes"})

        assert response.status_code == 403


class TestUpdateCourse:
    """PUT /courses/{course_id}"""

    def test_for_the_directors_own_department_returns_200(
        self, client, controller, auth
    ):
        """Test a valid payload updates the course in the director's department."""

        auth.as_user(DIRECTOR_USER)
        controller.update.return_value = {**COURSE, "name": "Redes"}

        response = client.put("/courses/1", json={"name": "Redes"})

        assert response.status_code == 200
        controller.update.assert_called_once()
        assert controller.update.call_args[0][2] == DIRECTOR_USER["department_id"]

    def test_when_course_missing_returns_404(self, client, controller, auth):
        """Test a None from the controller becomes a 404."""

        auth.as_user(DIRECTOR_USER)
        controller.update.return_value = None

        response = client.put("/courses/999", json={"name": "Redes"})

        assert response.status_code == 404

    def test_for_an_admin_returns_403(self, client, controller):
        """Test an ADMIN cannot update a course."""

        response = client.put("/courses/1", json={"name": "Redes"})

        assert response.status_code == 403


class TestDeleteCourse:
    """DELETE /courses/{course_id}"""

    def test_when_course_exists_returns_200(self, client, controller, auth):
        """Test deleting an existing course returns it."""

        auth.as_user(DIRECTOR_USER)
        controller.delete.return_value = COURSE

        response = client.delete("/courses/1")

        assert response.status_code == 200
        controller.delete.assert_called_once_with(1, DIRECTOR_USER["department_id"], DIRECTOR_USER)

    def test_when_course_missing_returns_404(self, client, controller, auth):
        """Test a None from the controller becomes a 404."""

        auth.as_user(DIRECTOR_USER)
        controller.delete.return_value = None

        response = client.delete("/courses/999")

        assert response.status_code == 404

    def test_for_an_admin_returns_403(self, client, controller):
        """Test an ADMIN cannot delete a course."""

        response = client.delete("/courses/1")

        assert response.status_code == 403
