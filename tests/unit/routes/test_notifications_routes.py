"""Tests for the notifications routes.

What the route layer owns here: any authenticated role may read/manage their
own notifications, only ADMIN/DIRECTOR may create one, and the current
user's id reaches the controller instead of a query parameter.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from api.controllers.notifications import get_notifications_controller
from api.routes.notifications import router
from tests.unit.routes.conftest import ADMIN_USER, DOCENTE_USER, paginated

NOTIFICATION = {
    "id": 1,
    "user_id": 3,
    "title": "Nuevo plan",
    "message": "Se creó un plan de mejoramiento",
    "type": "info",
    "read": False,
    "created_at": "2026-01-01T00:00:00Z",
    "updated_at": "2026-01-01T00:00:00Z",
}


@pytest.fixture
def controller():
    """Mock NotificationsController."""

    mock = MagicMock()
    mock.get_all = AsyncMock()
    mock.get_unread_count = AsyncMock()
    mock.create = AsyncMock()
    mock.mark_as_read = AsyncMock()
    mock.mark_all_as_read = AsyncMock()
    return mock


@pytest.fixture
def client(make_client, controller, auth):
    """Test client for the notifications router, authenticated as a teacher."""

    auth.as_user(DOCENTE_USER)
    return make_client(router, {get_notifications_controller: controller})


class TestListMyNotifications:
    """GET /notifications/me"""

    def test_returns_items_and_pagination(self, client, controller):
        """Test the paginated dict is split into data and pagination."""

        controller.get_all.return_value = paginated([NOTIFICATION])

        response = client.get("/notifications/me")

        assert response.status_code == 200
        assert response.json()["data"] == [NOTIFICATION]
        controller.get_all.assert_awaited_once()
        assert controller.get_all.call_args.args[0] == DOCENTE_USER["id"]

    def test_without_a_token_returns_401(self, client, controller, auth):
        """Test an anonymous request is rejected."""

        auth.anonymous()

        response = client.get("/notifications/me")

        assert response.status_code == 401


class TestUnreadCount:
    """GET /notifications/me/unread-count"""

    def test_returns_the_count(self, client, controller):
        """Test the count reaches the response body."""

        controller.get_unread_count.return_value = 3

        response = client.get("/notifications/me/unread-count")

        assert response.status_code == 200
        assert response.json()["data"]["unread_count"] == 3


class TestCreateNotification:
    """POST /notifications/"""

    def test_for_admin_returns_201(self, client, controller, auth):
        """Test an admin can create a notification."""

        auth.as_user(ADMIN_USER)
        controller.create.return_value = NOTIFICATION

        response = client.post(
            "/notifications/",
            json={"user_id": 3, "title": "Nuevo plan", "message": "Mensaje"},
        )

        assert response.status_code == 201
        controller.create.assert_awaited_once()

    def test_for_a_teacher_returns_403(self, client, controller):
        """Test a teacher cannot create notifications."""

        response = client.post(
            "/notifications/",
            json={"user_id": 3, "title": "Nuevo plan", "message": "Mensaje"},
        )

        assert response.status_code == 403
        controller.create.assert_not_called()


class TestMarkNotificationsRead:
    """PUT /notifications/me/read"""

    def test_returns_the_updated_count(self, client, controller):
        """Test the updated count reaches the response body."""

        controller.mark_as_read.return_value = 2

        response = client.put("/notifications/me/read", json={"ids": [1, 2]})

        assert response.status_code == 200
        assert response.json()["data"]["updated"] == 2
        controller.mark_as_read.assert_awaited_once_with([1, 2], DOCENTE_USER["id"])


class TestMarkAllNotificationsRead:
    """PUT /notifications/me/read-all"""

    def test_returns_the_updated_count(self, client, controller):
        """Test the updated count reaches the response body."""

        controller.mark_all_as_read.return_value = 5

        response = client.put("/notifications/me/read-all")

        assert response.status_code == 200
        assert response.json()["data"]["updated"] == 5
