"""Tests for the health route."""

from api.routes.health import router
from tests.unit.routes.conftest import DOCENTE_USER


class TestHealth:
    """GET /health/"""

    def test_returns_ok_without_authentication(self, make_client, auth):
        """Test the health check needs no token."""

        auth.anonymous()
        client = make_client(router)

        response = client.get("/health/")

        assert response.status_code == 200
        assert response.json()["data"]["status"] == "ok"

    def test_returns_ok_for_any_authenticated_user(self, make_client, auth):
        """Test the health check ignores the caller's role."""

        auth.as_user(DOCENTE_USER)
        client = make_client(router)

        response = client.get("/health/")

        assert response.status_code == 200
