"""Tests for the academic groups routes.

What the route layer owns here: the ADMIN/DIRECTOR guard and mapping a
``None`` from the controller to a 404.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from api.controllers.academic_groups import get_academic_groups_controller
from api.routes.academic_groups import router
from tests.unit.routes.conftest import DOCENTE_USER, paginated

GROUP = {
    "id": 1,
    "course_id": 1,
    "teacher_id": 1,
    "academic_period_id": 1,
    "group_name": "A",
    "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-01-01T00:00:00Z",
}


@pytest.fixture
def controller():
    """Mock AcademicGroupsController."""

    mock = MagicMock()
    mock.get_all = AsyncMock()
    mock.get_by_id = AsyncMock()
    mock.create = AsyncMock()
    mock.update = AsyncMock()
    mock.delete = AsyncMock()
    return mock


@pytest.fixture
def client(make_client, controller):
    """Test client for the academic groups router."""

    return make_client(router, {get_academic_groups_controller: controller})


class TestListAcademicGroups:
    """GET /academic-groups/"""

    def test_returns_items_and_pagination(self, client, controller):
        """Test the paginated dict is split into data and pagination."""

        controller.get_all.return_value = paginated([GROUP])

        response = client.get("/academic-groups/")

        assert response.status_code == 200
        assert response.json()["data"] == [GROUP]

    def test_for_a_teacher_returns_403(self, client, controller, auth):
        """Test a teacher cannot list academic groups."""

        auth.as_user(DOCENTE_USER)

        response = client.get("/academic-groups/")

        assert response.status_code == 403
        controller.get_all.assert_not_called()


class TestCreateAcademicGroup:
    """POST /academic-groups/"""

    def test_with_valid_payload_returns_201(self, client, controller):
        """Test a valid payload creates the group."""

        controller.create.return_value = GROUP

        response = client.post(
            "/academic-groups/",
            json={"course_id": 1, "teacher_id": 1, "academic_period_id": 1},
        )

        assert response.status_code == 201
        assert response.json()["data"]["id"] == 1

    def test_for_a_teacher_returns_403(self, client, controller, auth):
        """Test a teacher cannot create academic groups."""

        auth.as_user(DOCENTE_USER)

        response = client.post(
            "/academic-groups/",
            json={"course_id": 1, "teacher_id": 1, "academic_period_id": 1},
        )

        assert response.status_code == 403
        controller.create.assert_not_called()


class TestGetAcademicGroup:
    """GET /academic-groups/{group_id}"""

    def test_when_group_exists_returns_200(self, client, controller):
        """Test an existing group is returned in the envelope."""

        controller.get_by_id.return_value = GROUP

        response = client.get("/academic-groups/1")

        assert response.status_code == 200
        controller.get_by_id.assert_called_once_with(1)

    def test_when_group_missing_returns_404(self, client, controller):
        """Test a None from the controller becomes a 404."""

        controller.get_by_id.return_value = None

        response = client.get("/academic-groups/999")

        assert response.status_code == 404


class TestUpdateAcademicGroup:
    """PUT /academic-groups/{group_id}"""

    def test_with_valid_payload_returns_200(self, client, controller):
        """Test a valid payload updates the group."""

        controller.update.return_value = {**GROUP, "group_name": "B"}

        response = client.put("/academic-groups/1", json={"group_name": "B"})

        assert response.status_code == 200
        assert response.json()["data"]["group_name"] == "B"

    def test_when_group_missing_returns_404(self, client, controller):
        """Test a None from the controller becomes a 404."""

        controller.update.return_value = None

        response = client.put("/academic-groups/999", json={"group_name": "B"})

        assert response.status_code == 404


class TestDeleteAcademicGroup:
    """DELETE /academic-groups/{group_id}"""

    def test_when_group_exists_returns_200(self, client, controller):
        """Test deleting an existing group returns it."""

        controller.delete.return_value = GROUP

        response = client.delete("/academic-groups/1")

        assert response.status_code == 200

    def test_when_group_missing_returns_404(self, client, controller):
        """Test a None from the controller becomes a 404."""

        controller.delete.return_value = None

        response = client.delete("/academic-groups/999")

        assert response.status_code == 404
