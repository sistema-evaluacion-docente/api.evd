"""
Shared fixtures for route-level tests.

Each router under test is mounted on a bare FastAPI app carrying the same
envelope middleware and exception handlers as ``api.app``, so the tests cover
what the route layer itself does — role guards, department scoping, mapping a
``None`` from the controller to a 404 and the shape of the envelope — without
touching the database or Firebase.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.testclient import TestClient
from starlette.exceptions import HTTPException as StarletteHTTPException

from api.core.middleware import ResponseEnvelopeMiddleware
from api.dependencies.users import get_user_service
from api.exceptions import AppException
from api.exceptions.handlers import (
    app_exception_handler,
    generic_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from api.middlewares.auth import get_current_user
from api.schemas.user import RoleName, TokenUser

ADMIN_USER = {
    "id": 1,
    "uid": "admin-uid",
    "email": "admin@ufps.edu.co",
    "name": "Admin",
    "roles": [RoleName.ADMIN.value],
    "department_id": None,
}

DIRECTOR_USER = {
    "id": 2,
    "uid": "director-uid",
    "email": "director@ufps.edu.co",
    "name": "Director",
    "roles": [RoleName.DIRECTOR_DE_DEPARTAMENTO.value],
    "department_id": 7,
}

DOCENTE_USER = {
    "id": 3,
    "uid": "docente-uid",
    "email": "docente@ufps.edu.co",
    "name": "Docente",
    "roles": [RoleName.DOCENTE.value],
    "department_id": None,
}


class FakeAuth:
    """Controls what the auth dependencies resolve to during a test.

    ``as_user`` logs somebody in, ``anonymous`` drops the token (401) and
    setting ``db_user`` to None simulates a valid token for a user that is not
    in the database (404).
    """

    def __init__(self, user: dict | None = None):
        self.db_user = user
        self.token_user = self._token_for(user)

    @staticmethod
    def _token_for(user: dict | None) -> TokenUser | None:
        if user is None:
            return None

        return TokenUser(
            uid=user["uid"],
            email=user["email"],
            name=user["name"],
            picture="",
        )

    def as_user(self, user: dict) -> dict:
        """Authenticate the given user for the next request."""

        self.db_user = user
        self.token_user = self._token_for(user)
        return user

    def anonymous(self) -> None:
        """Drop the token so the next request is unauthenticated."""

        self.db_user = None
        self.token_user = None


@pytest.fixture
def auth():
    """Auth state for the test app, starting as an authenticated ADMIN."""

    return FakeAuth(ADMIN_USER)


@pytest.fixture
def make_client(auth):
    """Build a TestClient for a router with the auth and controller mocked out.

    ``overrides`` maps a dependency callable (typically the router's
    ``get_x_controller``) to the object that should replace it.
    """

    def _make_client(router, overrides: dict | None = None) -> TestClient:
        app = FastAPI()

        app.add_middleware(ResponseEnvelopeMiddleware)

        app.add_exception_handler(AppException, app_exception_handler)
        app.add_exception_handler(RequestValidationError, validation_exception_handler)
        app.add_exception_handler(StarletteHTTPException, http_exception_handler)
        app.add_exception_handler(Exception, generic_exception_handler)

        app.include_router(router)

        # `EnvelopeAPIRoute.get_route_handler` builds its handler from the
        # route's own state, so it never sees the provider FastAPI attaches
        # while handling an included route. Point the routes at this app so
        # `dependency_overrides` below actually apply.
        for route in router.routes:
            route.dependency_overrides_provider = app

        user_service = MagicMock()
        user_service.get_by_uid = AsyncMock(side_effect=lambda _uid: auth.db_user)

        app.dependency_overrides[get_current_user] = lambda: auth.token_user
        app.dependency_overrides[get_user_service] = lambda: user_service

        for dependency, replacement in (overrides or {}).items():
            app.dependency_overrides[dependency] = _returning(replacement)

        return TestClient(app, raise_server_exceptions=False)

    return _make_client


def _returning(value):
    """Build a zero-argument dependency that always resolves to ``value``.

    The closure matters: a `lambda value=value: value` would look like a query
    parameter to FastAPI, which deep-copies its default — the route would then
    get a copy of the mock and no call would be recorded on the original.
    """

    def _dependency():
        return value

    return _dependency


def paginated(items: list, total: int | None = None, page: int = 1, limit: int = 10):
    """Build the paginated dict a service returns, for use as a mock result."""

    count = len(items) if total is None else total

    return {
        "items": items,
        "total": count,
        "page": page,
        "limit": limit,
        "pages": (count + limit - 1) // limit if count else 0,
    }
