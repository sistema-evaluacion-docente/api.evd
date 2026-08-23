"""
Pytest configuration and shared fixtures.
"""

from unittest.mock import MagicMock
import pytest
from sqlalchemy.orm import Session

from api.config import config
from api.models.user import UserModel
from api.models.role import RoleModel
from api.schemas.user import UserCreate, RoleName


@pytest.fixture(autouse=True)
def _no_outgoing_mail(monkeypatch):
    """No test reaches a mail server, whatever the developer's ``.env`` says.

    A real one has ``MAIL_BACKEND=smtp`` with working credentials, and the
    services send best-effort — swallowing whatever goes wrong — so an
    unguarded suite quietly logs into that account and delivers to whatever
    address a fixture happened to invent. ``ConsoleBackend`` is the default for
    exactly this reason, but the default is not what runs here.

    Switched off at the flag rather than by patching the transport, so it covers
    every path into it. The few tests that are *about* the mail turn it back on
    themselves, with the backend patched.
    """

    monkeypatch.setattr(config, "MAIL_ENABLED", False)


@pytest.fixture
def mock_db():
    """Mock database session."""

    db = MagicMock(spec=Session)
    return db


@pytest.fixture
def mock_user_model():
    """Mock UserModel instance."""

    user = MagicMock(spec=UserModel)
    user.id = 1
    user.uid = "test-uid-123"
    user.email = "test@example.com"
    user.name = "Test User"
    user.active = True
    user.avatar_url = None
    user.teacher = None
    return user


@pytest.fixture
def mock_role_model():
    """Mock RoleModel instance."""

    role = MagicMock(spec=RoleModel)
    role.id = 1
    role.name = "DOCENTE"
    return role


@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""

    return {
        "uid": "test-uid-123",
        "email": "test@example.com",
        "name": "Test User",
        "active": True,
        "avatar_url": None,
    }


@pytest.fixture
def sample_user_create():
    """Sample UserCreate schema."""

    return UserCreate(
        uid="test-uid-123",
        email="test@example.com",
        name="Test User",
        active=True,
        roles=[RoleName.DOCENTE],
    )
