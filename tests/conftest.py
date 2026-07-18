"""
Pytest configuration and shared fixtures.
"""

from unittest.mock import MagicMock
import pytest
from sqlalchemy.orm import Session

from api.models.user import UserModel
from api.models.role import RoleModel
from api.schemas.user import UserCreate, RoleName


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
    user.username = "testuser"
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
        "username": "testuser",
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
        username="testuser",
        name="Test User",
        active=True,
        roles=[RoleName.DOCENTE],
    )
