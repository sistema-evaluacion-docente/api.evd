"""User Controllers"""

from fastapi.param_functions import Depends

from api.core.pagination import PaginationParams
from api.dependencies.users import get_user_service
from api.schemas.user import (
    UserCreate,
    UserFilters,
    UserRolesUpdate,
    UserStatusUpdate,
    UserUpdate,
)
from api.services.user_service import UserService


class UsersController:
    """Controller for user-related operations."""

    def __init__(self, service: UserService):
        self.service = service

    async def login(self, current_user):
        """Handle user login."""

        return await self.service.login(current_user)

    async def get_all(
        self,
        filters: UserFilters,
        pagination: PaginationParams,
    ):
        """Retrieve all users based on filters and pagination."""

        return await self.service.get_all(filters, pagination)

    async def get_by_uid(self, uid: str):
        """Retrieve a user by their unique identifier."""

        return await self.service.get_by_uid(uid)

    async def update(self, payload: UserUpdate, current_user):
        """Update user information."""

        return await self.service.update_user(current_user.uid, payload)

    async def replace_roles(
        self,
        uid: str,
        payload: UserRolesUpdate,
        current_user,
    ):
        """Replace user roles."""

        return await self.service.replace_roles(uid, payload, current_user)

    async def update_status(self, uid: str, payload: UserStatusUpdate):
        """Update the status of a user."""

        return await self.service.update_status(uid, payload)

    async def create_user(self, data: UserCreate, current_user):
        """Create a new user."""

        return await self.service.create_user(data, current_user)


def get_users_controller(
    service: UserService = Depends(get_user_service),
):
    """Dependency injection for UsersController."""

    return UsersController(service)
