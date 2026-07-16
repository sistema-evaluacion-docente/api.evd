"""
Routes for user-related operations.
"""

from fastapi import APIRouter, Depends, Query

from api.controllers.users import UsersController, get_users_controller
from api.middlewares.auth import get_current_user, require_roles
from api.schemas.pagination import Pagination
from api.schemas.response import ResponseSchema
from api.schemas.user import (
    RoleName,
    UserCreate,
    UserDetailResponse,
    UserListResponse,
    UserRolesUpdate,
    UserStatusUpdate,
    UserUpdate,
)

router = APIRouter(prefix="/users", tags=["Users"])


@router.post(
    "/",
    response_model=UserDetailResponse,
    responses={400: {"model": ResponseSchema}, 403: {"description": "Forbidden"}},
)
async def create_user(
    payload: UserCreate,
    current_user=Depends(get_current_user),
    _=Depends(require_roles([RoleName.ADMIN, RoleName.DIRECTOR_DE_DEPARTAMENTO])),
    controller: UsersController = Depends(get_users_controller),
):
    """Endpoint to create a new user. ADMIN can create any role, DIRECTOR can only create DOCENTE."""

    try:
        user = await controller.create_user(payload, current_user)
    except ValueError as e:
        return ResponseSchema(
            status=400, message=str(e), path="/users"
        )

    if not user:
        return ResponseSchema(
            status=400, message="Error creating user", path="/users"
        )

    return ResponseSchema(
        status=201,
        message="User created successfully",
        data=user,
        path="/users",
    )


@router.get(
    "/",
    response_model=UserListResponse,
    responses={403: {"description": "Forbidden"}},
)
async def get_all_users(
    search: str | None = Query(default=None, min_length=1),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=100),
    _=Depends(require_roles([RoleName.ADMIN])),
    controller: UsersController = Depends(get_users_controller),
):
    """Endpoint to get all users."""

    users = await controller.get_all(search=search, page=page, limit=limit)

    if users is None:
        return ResponseSchema(status=400, message="Error getting users", path="/users")

    return ResponseSchema(
        status=200,
        data=users["items"],
        pagination=Pagination(
            limit=users["limit"],
            total=users["total"],
            pages=users["pages"],
            page=users["page"],
        ),
        message="Users found",
        path="/users",
    )


@router.get(
    "/auth",
    response_model=UserDetailResponse,
    responses={401: {"model": ResponseSchema}},
)
async def login_user(
    current_user=Depends(get_current_user),
    controller: UsersController = Depends(get_users_controller),
):
    """Endpoint to verify user login."""

    user = await controller.login(current_user)

    if not user:
        return ResponseSchema(
            status=401,
            message="Autenticación fallida",
            path="/users/auth"
        )

    return ResponseSchema(
        status=200, message="Autenticación exitosa", data=user, path="/users/auth"
    )


@router.get(
    "/{uid}",
    response_model=UserDetailResponse,
    responses={401: {"model": ResponseSchema}},
)
async def get_user_by_uid(
    uid: str,
    _=Depends(get_current_user),
    controller: UsersController = Depends(get_users_controller),
):
    """Endpoint to get user information by UID."""

    user = await controller.get_by_uid(uid)

    if not user:
        return ResponseSchema(
            status=401, message="User not found", path=f"/users/{uid}"
        )

    return ResponseSchema(
        status=200, message="User found", data=user, path=f"/users/{uid}"
    )


@router.put(
    "/",
    response_model=UserDetailResponse,
    responses={400: {"model": ResponseSchema}},
)
async def update_user(
    payload: UserUpdate,
    current_user=Depends(get_current_user),
    controller: UsersController = Depends(get_users_controller),
):
    """Endpoint to update user information."""

    user = await controller.update(payload, current_user)

    if not user:
        return ResponseSchema(status=400, message="Error updating user", path="/users")

    return ResponseSchema(
        status=200, message="User updated successfully", data=user, path="/users"
    )


@router.put(
    "/{uid}/roles",
    response_model=UserDetailResponse,
    responses={400: {"model": ResponseSchema}},
)
async def replace_user_roles(
    uid: str,
    payload: UserRolesUpdate,
    current_user=Depends(get_current_user),
    _=Depends(require_roles([RoleName.ADMIN])),
    controller: UsersController = Depends(get_users_controller),
):
    """Endpoint to replace all roles for a user."""

    try:
        result = await controller.replace_roles(uid, payload, current_user)

        if not result:
            return ResponseSchema(
                status=400, message="Error updating roles", path=f"/users/{uid}/roles"
            )
    except ValueError as e:
        return ResponseSchema(status=400, message=str(e), path=f"/users/{uid}/roles")

    return ResponseSchema(
        status=200,
        message="Roles updated successfully",
        data=result,
        path=f"/users/{uid}/roles",
    )


@router.patch(
    "/{uid}/status",
    response_model=UserDetailResponse,
    responses={400: {"model": ResponseSchema}, 403: {"description": "Forbidden"}},
)
async def update_user_status(
    uid: str,
    payload: UserStatusUpdate,
    _=Depends(require_roles([RoleName.ADMIN])),
    controller: UsersController = Depends(get_users_controller),
):
    """Endpoint to activate/deactivate a user."""

    result = await controller.update_status(uid, payload)

    if not result:
        return ResponseSchema(
            status=400,
            message="Error updating user status",
            path=f"/users/{uid}/status",
        )

    return ResponseSchema(
        status=200,
        message="User status updated successfully",
        data=result,
        path=f"/users/{uid}/status",
    )
