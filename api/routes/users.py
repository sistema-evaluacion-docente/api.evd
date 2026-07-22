"""
Routes for user-related operations.
"""

from fastapi import Depends

from api.controllers.users import UsersController, get_users_controller
from api.core.pagination import PaginationDep
from api.middlewares.auth import get_current_user, require_roles
from api.schemas.user import (
    RoleName,
    UserCreate,
    UserFiltersDep,
    UserOut,
    UserRolesUpdate,
    UserStatusUpdate,
    UserUpdate,
)
from api.exceptions import AuthenticationError
from api.exceptions import UserNotFoundError
from api.core.router import EnvelopeRouter

router = EnvelopeRouter(prefix="/users", tags=["Users"])


@router.post(
    "/",
    status_code=201,
    response_model=UserOut,
)
async def create_user(
    payload: UserCreate,
    current_user=Depends(get_current_user),
    _=Depends(require_roles([RoleName.ADMIN, RoleName.DIRECTOR_DE_DEPARTAMENTO])),
    controller: UsersController = Depends(get_users_controller),
):
    """
    Create a new user. ADMIN can create any role, DIRECTOR can only create DOCENTE.
    """

    return await controller.create_user(payload, current_user)


@router.get("/", response_model=list[UserOut])
async def get_all_users(
    filters: UserFiltersDep,
    pagination: PaginationDep,
    _=Depends(require_roles([RoleName.ADMIN])),
    controller: UsersController = Depends(get_users_controller),
):
    """
    Get all users with pagination and optional search.

    Response: ResponseEnvelope[list[UserOut]]
    """

    return await controller.get_all(filters, pagination)


@router.get(
    "/auth",
    response_model=UserOut,
)
async def login_user(
    current_user=Depends(get_current_user),
    controller: UsersController = Depends(get_users_controller),
):
    """
    Verify user login and return user data.

    Response: ResponseEnvelope[UserOut]
    """

    user = await controller.login(current_user)

    if not user:
        raise AuthenticationError("Autenticación fallida")

    return user


@router.get(
    "/{uid}",
    response_model=UserOut,
)
async def get_user_by_uid(
    uid: str,
    _=Depends(get_current_user),
    controller: UsersController = Depends(get_users_controller),
):
    """
    Get user information by Firebase UID.

    Response: ResponseEnvelope[UserOut]
    """

    user = await controller.get_by_uid(uid)

    if not user:
        raise UserNotFoundError(uid)

    return user


@router.put(
    "/",
    response_model=UserOut,
)
async def update_user(
    payload: UserUpdate,
    current_user=Depends(get_current_user),
    controller: UsersController = Depends(get_users_controller),
):
    """
    Update the authenticated user's profile.

    Response: ResponseEnvelope[UserOut]
    """

    return await controller.update(payload, current_user)


@router.put(
    "/{uid}/roles",
    response_model=UserOut,
)
async def replace_user_roles(
    uid: str,
    payload: UserRolesUpdate,
    current_user=Depends(get_current_user),
    _=Depends(require_roles([RoleName.ADMIN])),
    controller: UsersController = Depends(get_users_controller),
):
    """
    Replace all roles for a user. ADMIN only.

    Response: ResponseEnvelope[UserOut]
    """

    return await controller.replace_roles(uid, payload, current_user)


@router.patch(
    "/{uid}/status",
    response_model=UserOut,
)
async def update_user_status(
    uid: str,
    payload: UserStatusUpdate,
    _=Depends(require_roles([RoleName.ADMIN])),
    controller: UsersController = Depends(get_users_controller),
):
    """
    Activate or deactivate a user. ADMIN only.

    Response: ResponseEnvelope[UserOut]
    """

    return await controller.update_status(uid, payload)
