"""ASGI entrypoint for the local stress-test environment.

Runs the real FastAPI app but swaps Firebase token verification for a plain
header read, so the load generator never has to mint real Firebase ID
tokens. Everything downstream of `get_current_user` still runs unmodified
against the Neon "stress-test" branch: `require_roles` still calls
`user_service.get_by_uid` for the real user row and does the real role
check, so authorization behaves exactly like production for whichever uid
the load test sends.

Only ever run via docker-compose.stress.yaml (see its `command`). Never
imported by api/app.py and never part of docker/Dockerfile's default
entrypoint — this bypass must stay confined to the local stress-test
environment.
"""

from fastapi import Header

from api.app import app
from api.middlewares.auth import get_current_user
from api.schemas.user import TokenUser


def fake_current_user(x_test_uid: str | None = Header(default=None)) -> TokenUser | None:
    """Trust a caller-supplied uid instead of verifying a Firebase token."""

    if not x_test_uid:
        return None

    return TokenUser(
        uid=x_test_uid,
        email=f"{x_test_uid}@stress.test",
        name=x_test_uid,
        picture="",
    )


def _rebind_dependency_overrides_provider(target_app) -> None:
    """Point every included router's routes at ``target_app``.

    ``EnvelopeAPIRoute.get_route_handler`` (api/core/router.py) builds its
    request handler from the route's own ``dependency_overrides_provider``.
    The installed FastAPI wraps each ``app.include_router(...)`` call in an
    internal ``_IncludedRouter`` instead of eagerly re-registering routes
    on the app, so that attribute is never set for a routed endpoint and
    ``app.dependency_overrides`` is silently ignored everywhere except
    routes declared directly on ``app``. `tests/unit/routes/conftest.py`
    hits the same issue for its single-router test apps and fixes it the
    same way; here it has to walk every router api/app.py includes.
    """

    seen: set[int] = set()
    stack = list(target_app.routes)
    while stack:
        route = stack.pop()
        if id(route) in seen:
            continue
        seen.add(id(route))

        original_router = getattr(route, "original_router", None)
        if original_router is not None:
            stack.extend(original_router.routes)
            continue

        if hasattr(route, "dependency_overrides_provider"):
            route.dependency_overrides_provider = target_app


_rebind_dependency_overrides_provider(app)
app.dependency_overrides[get_current_user] = fake_current_user
