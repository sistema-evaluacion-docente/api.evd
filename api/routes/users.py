"""
Routes for user-related operations.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from api.controllers.users import UsersController, get_users_controller
from api.middlewares.auth import get_current_user
from api.repositories.users import UsersRepository, get_users_repository
from api.schemas.response import ResponseSchema
from api.schemas.user import UserUpdate

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
    repository: UsersRepository = Depends(get_users_repository),
):
    """Endpoint to get user information by UID."""

    try:
        user = await repository.get_by_uid(uid)
    except ValueError as e:
        return {"error": str(e), "status": 404, "timestamp": datetime.now(timezone.utc)}

    return {
        "data": user,
        "error": None,
        "status": 200,
        "timestamp": datetime.now(timezone.utc),
    }


@router.get("/")
async def get_user(
    current_user=Depends(get_current_user),
    repository: UsersRepository = Depends(get_users_repository),
):
    """Endpoint to get current user information."""

    try:
        user = await repository.get_by_uid(current_user.uid)
    except ValueError as e:
        return {"error": str(e), "status": 404, "timestamp": datetime.now(timezone.utc)}

    return {"user": user}


@router.put("/")
async def update_user(
    payload: UserUpdate,
    current_user=Depends(get_current_user),
    repository: UsersRepository = Depends(get_users_repository),
):
    """Endpoint to update user information."""

    try:
        updated_user = await repository.update(current_user.uid, payload)
    except ValueError as e:
        return {"error": str(e)}

    return {"message": "User updated successfully", "user": updated_user}
