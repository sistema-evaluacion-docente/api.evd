"""
Routes for user-related operations.
"""

from fastapi import APIRouter, Depends

from api.controllers.users import UsersController, get_users_controller
from api.middlewares.auth import get_current_user, require_roles
from api.schemas.response import ResponseSchema
from api.schemas.user import RoleName, UserRolesUpdate, UserUpdate

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/auth")
async def login_user(
    current_user=Depends(get_current_user),
    controller: UsersController = Depends(get_users_controller),
):
    """Endpoint to verify user login."""

    user = await controller.login(current_user)

    if not user:
        return ResponseSchema(
            status=401, message="Authentication failed", path="/users/auth"
        )

    return ResponseSchema(
        status=200, message="Authentication successful", data=user, path="/users/auth"
    )


@router.get("/{uid}")
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


@router.put("/")
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


@router.put("/{uid}/roles")
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
