"""
Where a plan lives in the SPA.

The two routes are stated once, here, because two different channels send people
to them — the notification bell, with a relative path the app routes itself, and
the email, which needs an absolute URL. Spelling them out at each call site is
how the bell ended up sending teachers to the director's screen.
"""

from api.config import config


def teacher_plan_path(plan_id: int) -> str:
    """The teacher's own view of their plan."""

    return f"/mis-planes/{plan_id}"


def manager_plan_path(plan_id: int) -> str:
    """The director's view, where the plan is managed."""

    return f"/planes/{plan_id}"


def absolute(path: str) -> str:
    """The same route, reachable from outside the app.

    An email has no router to resolve "/mis-planes/7" against, so it needs the
    deployment's own base URL in front of it.
    """

    return f"{config.FRONTEND_URL}{path}"
